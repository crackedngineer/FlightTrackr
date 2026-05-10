from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_db_session
from app.services import flight_service
from app.schemas.flight_schema import BookingsListResponse, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/", response_model=BookingsListResponse, summary="List user bookings")
async def list_bookings(
    status: Optional[str] = Query(None, description="Filter: upcoming | completed"),
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BookingsListResponse:
    bookings = await flight_service.list_bookings(
        session, user_id, status_filter=status
    )
    return BookingsListResponse(
        bookings=[BookingResponse.from_orm(b) for b in bookings], total=len(bookings)
    )


@router.get(
    "/{booking_id}", response_model=BookingResponse, summary="Get booking by ID"
)
async def get_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BookingResponse:
    booking = await flight_service.get_booking(session, user_id, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingResponse.from_orm(booking)


@router.delete("/{booking_id}", status_code=204, summary="Delete booking")
async def delete_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await flight_service.delete_booking(session, user_id, booking_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Booking not found")
