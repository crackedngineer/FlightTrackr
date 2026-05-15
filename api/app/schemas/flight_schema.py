from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AirportInfo(BaseModel):
    iata_code: str
    name: Optional[str] = None
    city: Optional[str] = None


class AirlineInfo(BaseModel):
    iata_code: str
    name: Optional[str] = None


class PassengerInfo(BaseModel):
    first_name: str
    last_name: str


class BoardingPassResponse(BaseModel):
    id: str
    passenger: PassengerInfo
    seat_number: Optional[str] = None
    cabin_class: Optional[str] = None
    boarding_group: Optional[str] = None
    barcode: str


class FlightResponse(BaseModel):
    id: str
    flight_number: str
    airline: AirlineInfo
    departure_airport: AirportInfo
    departure_time: str
    arrival_airport: AirportInfo
    arrival_time: Optional[str] = None
    gate: Optional[str] = None
    terminal: Optional[str] = None
    status: str
    boarding_passes: list[BoardingPassResponse]


class BookingResponse(BaseModel):
    id: str
    pnr_code: str
    booking_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    airline: AirlineInfo
    source: str
    flights: list[FlightResponse]

    @classmethod
    def from_orm(cls, booking) -> "BookingResponse":
        def fmt(dt) -> Optional[str]:
            if dt is None:
                return None
            return dt.isoformat() if isinstance(dt, (datetime, date)) else str(dt)

        segments = []
        for f in (booking.flights or []):
            bps = []
            for bp in (f.boarding_passes or []):
                bps.append(BoardingPassResponse(
                    id=str(bp.id),
                    passenger=PassengerInfo(
                        first_name=bp.passenger.first_name if bp.passenger else "",
                        last_name=bp.passenger.last_name if bp.passenger else "",
                    ),
                    seat_number=bp.seat_number,
                    cabin_class=bp.cabin_class,
                    boarding_group=bp.boarding_group,
                    barcode=bp.barcode or "",
                ))
            segments.append(FlightResponse(
                id=str(f.id),
                flight_number=f.flight_number,
                airline=AirlineInfo(
                    iata_code=f.airline_rel.iata_code if f.airline_rel else "",
                    name=f.airline_rel.name if f.airline_rel else None,
                ),
                departure_airport=AirportInfo(
                    iata_code=f.dep_airport.iata_code if f.dep_airport else "",
                    name=f.dep_airport.name if f.dep_airport else None,
                    city=f.dep_airport.city if f.dep_airport else None,
                ),
                departure_time=fmt(f.departure_time) or "",
                arrival_airport=AirportInfo(
                    iata_code=f.arr_airport.iata_code if f.arr_airport else "",
                    name=f.arr_airport.name if f.arr_airport else None,
                    city=f.arr_airport.city if f.arr_airport else None,
                ),
                arrival_time=fmt(f.arrival_time),
                gate=f.gate,
                terminal=f.terminal,
                status=f.status,
                boarding_passes=bps,
            ))

        return cls(
            id=str(booking.id),
            pnr_code=booking.pnr_code,
            booking_type=booking.booking_type,
            start_date=fmt(booking.start_date),
            end_date=fmt(booking.end_date),
            airline=AirlineInfo(
                iata_code=booking.airline_rel.iata_code if booking.airline_rel else "",
                name=booking.airline_rel.name if booking.airline_rel else None,
            ),
            source=booking.source,
            flights=segments,
        )


class BookingsListResponse(BaseModel):
    bookings: list[BookingResponse]
    total: int
