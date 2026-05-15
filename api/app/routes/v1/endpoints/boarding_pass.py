"""
Boarding pass parsing endpoints.
Handles PDF boarding pass uploads and parsing operations.
"""

from datetime import date
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.core.exceptions import BoardingPassParsingException
from app.parsers.factory import ParserFactory
from app.schemas.flight_schema import BookingResponse
from app.services import flight_service
from app.services.parser_service import BoardingPassService


def get_boarding_pass_service() -> BoardingPassService:
    return BoardingPassService(factory=ParserFactory())


router = APIRouter(prefix="/boarding-pass")

_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _validate_pdf(file: UploadFile) -> None:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )
    if file.size and file.size > _MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Maximum size is 5MB",
        )

@router.post(
    "/upload",
    response_model=BookingResponse,
    summary="Upload and save boarding pass",
    description="Upload a boarding pass PDF, parse it, and save the flight to your account.",
)
async def upload_boarding_pass(
    file: UploadFile = File(..., description="Boarding pass PDF file"),
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    parser_service: BoardingPassService = Depends(get_boarding_pass_service),
) -> BookingResponse:
    _validate_pdf(file)

    # Parse PDF
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded")
        parsed = parser_service.process(pdf_bytes)
    except BoardingPassParsingException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during parsing",
        )

    # Validate required parsed fields
    missing = [f for f, v in [
        ("operator_code", parsed.operator_code),
        ("origin", parsed.origin),
        ("destination", parsed.destination),
        ("departure_time", parsed.departure_time),
        ("pnr_code", parsed.pnr_code),
    ] if not v]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract required fields from boarding pass: {', '.join(missing)}",
        )

    # Resolve airline
    airline = await flight_service.get_airline_by_iata_async(session, str(parsed.operator_code))
    if not airline:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Airline '{parsed.operator_code}' not found in database",
        )

    # Resolve airports
    dep_airport = await flight_service.get_airport_by_iata_async(session, str(parsed.origin))
    arr_airport = await flight_service.get_airport_by_iata_async(session, str(parsed.destination))
    if not dep_airport:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Departure airport '{parsed.origin}' not found in database",
        )
    if not arr_airport:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Arrival airport '{parsed.destination}' not found in database",
        )

    # Parse departure datetime
    departure_dt = flight_service._parse_departure_to_datetime(parsed.departure_time)
    if not departure_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse departure time: '{parsed.departure_time}'",
        )

    flight_status = "upcoming" if departure_dt.date() >= date.today() else "completed"
    flight_number = f"{(parsed.operator_code or '').strip()}{(parsed.flight_number or '').strip()}"

    # Persist
    booking = await flight_service.upsert_booking_async(
        session, user_id, airline.id, str(parsed.pnr_code), source="upload"
    )
    flight = await flight_service.upsert_flight_async(
        session,
        booking_id=booking.id,
        airline_id=airline.id,
        dep_airport_id=dep_airport.id,
        arr_airport_id=arr_airport.id,
        flight_number=flight_number,
        departure_time=departure_dt,
    )
    flight.status = flight_status

    passenger = await flight_service.upsert_passenger_async(
        session, booking.id, parsed.passenger_firstname, parsed.passenger_lastname
    )
    await flight_service.upsert_boarding_pass_async(
        session,
        flight_id=flight.id,
        passenger_id=passenger.id,
        barcode=parsed.barcode or flight_number,
        seat_number=parsed.seat_number,
        cabin_class=parsed.cabin_class,
        boarding_group=parsed.boarding_group,
        source="upload",
    )
    await flight_service.update_booking_metadata_async(session, booking.id)
    await session.commit()

    saved = await flight_service.get_booking(session, user_id, str(booking.id))
    return BookingResponse.from_orm(saved)