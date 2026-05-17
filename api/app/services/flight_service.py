import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.flight import Booking, Flight, Passenger, BoardingPass
from app.models.airline import Airline
from app.models.airport import Airport
import logging

logger = logging.getLogger(__name__)


def _parse_departure_to_datetime(dep_time_str: Optional[str]) -> Optional[datetime]:
    if not dep_time_str:
        return None
    try:
        return datetime.fromisoformat(dep_time_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        d = datetime.strptime(dep_time_str, "%d/%b")
        today = date.today()
        candidate = d.replace(year=today.year).date()
        if candidate < today:
            candidate = candidate.replace(year=today.year + 1)
        return datetime(candidate.year, candidate.month, candidate.day)
    except ValueError:
        pass
    return None


# ── Sync lookup helpers ───────────────────────────────────────────────────────


def get_airline_by_iata_sync(session: Session, iata_code: str) -> Optional[Airline]:
    return session.execute(
        select(Airline).where(Airline.iata_code == iata_code.upper().strip())
    ).scalar_one_or_none()


def get_airport_by_iata_sync(session: Session, iata_code: str) -> Optional[Airport]:
    return session.execute(
        select(Airport).where(Airport.iata_code == iata_code.upper().strip())
    ).scalar_one_or_none()


# ── Sync upsert operations (Celery) ──────────────────────────────────────────


def upsert_booking_sync(
    session: Session,
    user_id: str,
    airline_id: int,
    pnr_code: str,
    source: str = "gmail",
) -> Booking:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    existing = session.execute(
        select(Booking).where(
            Booking.user_id == uid,
            Booking.airline_id == airline_id,
            Booking.pnr_code == pnr_code,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    booking = Booking(
        user_id=uid, airline_id=airline_id, pnr_code=pnr_code, source=source
    )
    session.add(booking)
    session.flush()
    return booking


def upsert_flight_sync(
    session: Session,
    booking_id: uuid.UUID,
    airline_id: int,
    dep_airport_id: uuid.UUID,
    arr_airport_id: uuid.UUID,
    flight_number: str,
    departure_time: datetime,
    arrival_time: Optional[datetime] = None,
    gate: Optional[str] = None,
    terminal: Optional[str] = None,
) -> Flight:
    existing = session.execute(
        select(Flight).where(
            Flight.booking_id == booking_id,
            Flight.flight_number == flight_number,
            Flight.airline_id == airline_id,
            Flight.departure_time == departure_time,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    flight = Flight(
        booking_id=booking_id,
        airline_id=airline_id,
        departure_airport=dep_airport_id,
        arrival_airport=arr_airport_id,
        flight_number=flight_number,
        departure_time=departure_time,
        arrival_time=arrival_time,
        gate=gate,
        terminal=terminal,
    )
    session.add(flight)
    session.flush()
    return flight


def upsert_passenger_sync(
    session: Session,
    booking_id: uuid.UUID,
    first_name: Optional[str],
    last_name: Optional[str],
) -> Passenger:
    fn, ln = (first_name or "").strip(), (last_name or "").strip()
    existing = session.execute(
        select(Passenger).where(
            Passenger.booking_id == booking_id,
            Passenger.first_name == fn,
            Passenger.last_name == ln,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    passenger = Passenger(booking_id=booking_id, first_name=fn, last_name=ln)
    session.add(passenger)
    session.flush()
    return passenger


def upsert_boarding_pass_sync(
    session: Session,
    flight_id: uuid.UUID,
    passenger_id: uuid.UUID,
    barcode: str,
    seat_number: Optional[str] = None,
    cabin_class: Optional[str] = None,
    boarding_group: Optional[str] = None,
    source: Optional[str] = None,
    source_message_id: Optional[str] = None,
) -> BoardingPass:
    existing = session.execute(
        select(BoardingPass).where(
            BoardingPass.flight_id == flight_id,
            BoardingPass.passenger_id == passenger_id,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    bp = BoardingPass(
        flight_id=flight_id,
        passenger_id=passenger_id,
        barcode=barcode,
        seat_number=seat_number,
        cabin_class=cabin_class,
        boarding_group=boarding_group,
        source=source,
        source_message_id=source_message_id,
    )
    session.add(bp)
    session.flush()
    return bp


def update_booking_metadata_sync(session: Session, booking_id: uuid.UUID) -> None:
    flights = (
        session.execute(
            select(Flight)
            .where(Flight.booking_id == booking_id)
            .order_by(Flight.departure_time)
        )
        .scalars()
        .all()
    )
    if not flights:
        return
    booking = session.get(Booking, booking_id)
    if not booking:
        return
    booking.booking_type = "direct" if len(flights) == 1 else "connecting"
    booking.start_date = (
        flights[0].departure_time.date() if flights[0].departure_time else None
    )
    booking.end_date = (
        flights[-1].departure_time.date() if flights[-1].departure_time else None
    )


def get_existing_message_ids_sync(
    session: Session, user_id: str, source: str, message_ids: list[str]
) -> set[str]:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    rows = (
        session.execute(
            select(BoardingPass.source_message_id)
            .join(Flight, BoardingPass.flight_id == Flight.id)
            .join(Booking, Flight.booking_id == Booking.id)
            .where(
                Booking.user_id == uid,
                BoardingPass.source == source,
                BoardingPass.source_message_id.in_(message_ids),
            )
        )
        .scalars()
        .all()
    )
    return set(rows)


# ── Async lookup helpers ─────────────────────────────────────────────────────


async def get_airline_by_iata_async(
    session: AsyncSession, iata_code: str
) -> Optional[Airline]:
    result = await session.execute(
        select(Airline).where(Airline.iata_code == iata_code.upper().strip())
    )
    return result.scalar_one_or_none()


async def get_airport_by_iata_async(
    session: AsyncSession, iata_code: str
) -> Optional[Airport]:
    result = await session.execute(
        select(Airport).where(Airport.iata_code == iata_code.upper().strip())
    )
    return result.scalar_one_or_none()


# ── Async upsert operations (FastAPI) ────────────────────────────────────────


async def upsert_booking_async(
    session: AsyncSession,
    user_id: str,
    airline_id: int,
    pnr_code: str,
    source: str = "upload",
) -> Booking:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    await session.execute(
        pg_insert(Booking)
        .values(user_id=uid, airline_id=airline_id, pnr_code=pnr_code, source=source)
        .on_conflict_do_nothing(constraint="uq_bookings_user_airline_pnr")
    )
    result = await session.execute(
        select(Booking).where(
            Booking.user_id == uid,
            Booking.airline_id == airline_id,
            Booking.pnr_code == pnr_code,
        )
    )
    return result.scalar_one()


async def upsert_flight_async(
    session: AsyncSession,
    booking_id: uuid.UUID,
    airline_id: int,
    dep_airport_id: uuid.UUID,
    arr_airport_id: uuid.UUID,
    flight_number: str,
    departure_time: datetime,
    arrival_time: Optional[datetime] = None,
    gate: Optional[str] = None,
    terminal: Optional[str] = None,
) -> Flight:
    await session.execute(
        pg_insert(Flight)
        .values(
            booking_id=booking_id,
            airline_id=airline_id,
            departure_airport=dep_airport_id,
            arrival_airport=arr_airport_id,
            flight_number=flight_number,
            departure_time=departure_time,
            arrival_time=arrival_time,
            gate=gate,
            terminal=terminal,
        )
        .on_conflict_do_nothing(constraint="uq_flights_booking_flight_dep")
    )
    result = await session.execute(
        select(Flight).where(
            Flight.booking_id == booking_id,
            Flight.flight_number == flight_number,
            Flight.airline_id == airline_id,
            Flight.departure_time == departure_time,
        )
    )
    return result.scalar_one()


async def upsert_passenger_async(
    session: AsyncSession,
    booking_id: uuid.UUID,
    first_name: Optional[str],
    last_name: Optional[str],
) -> Passenger:
    fn, ln = (first_name or "").strip(), (last_name or "").strip()
    await session.execute(
        pg_insert(Passenger)
        .values(booking_id=booking_id, first_name=fn, last_name=ln)
        .on_conflict_do_nothing(constraint="uq_passengers_booking_name")
    )
    result = await session.execute(
        select(Passenger).where(
            Passenger.booking_id == booking_id,
            Passenger.first_name == fn,
            Passenger.last_name == ln,
        )
    )
    return result.scalar_one()


async def upsert_boarding_pass_async(
    session: AsyncSession,
    flight_id: uuid.UUID,
    passenger_id: uuid.UUID,
    barcode: str,
    seat_number: Optional[str] = None,
    cabin_class: Optional[str] = None,
    boarding_group: Optional[str] = None,
    source: Optional[str] = None,
) -> BoardingPass:
    # Conflict on barcode (globally unique) with UPDATE so that if a re-upload
    # produces a different flight_id (due to departure_time drift), the boarding
    # pass is re-linked to the current flight rather than causing an IntegrityError.
    await session.execute(
        pg_insert(BoardingPass)
        .values(
            flight_id=flight_id,
            passenger_id=passenger_id,
            barcode=barcode,
            seat_number=seat_number,
            cabin_class=cabin_class,
            boarding_group=boarding_group,
            source=source,
        )
        .on_conflict_do_update(
            constraint="uq_boarding_passes_barcode",
            set_=dict(
                flight_id=flight_id,
                passenger_id=passenger_id,
                seat_number=seat_number,
                cabin_class=cabin_class,
                boarding_group=boarding_group,
            ),
        )
    )
    result = await session.execute(
        select(BoardingPass).where(BoardingPass.barcode == barcode)
    )
    return result.scalar_one()


async def update_booking_metadata_async(
    session: AsyncSession, booking_id: uuid.UUID
) -> None:
    result = await session.execute(
        select(Flight)
        .where(Flight.booking_id == booking_id)
        .order_by(Flight.departure_time)
    )
    flights = result.scalars().all()
    if not flights:
        return
    booking = await session.get(Booking, booking_id)
    if not booking:
        return
    booking.booking_type = "direct" if len(flights) == 1 else "connecting"
    booking.start_date = flights[0].departure_time.date() if flights[0].departure_time else None
    booking.end_date = flights[-1].departure_time.date() if flights[-1].departure_time else None


# ── Async CRUD (FastAPI) ──────────────────────────────────────────────────────


def _booking_load_options():
    return [
        selectinload(Booking.airline_rel),
        selectinload(Booking.flights).options(
            selectinload(Flight.dep_airport),
            selectinload(Flight.arr_airport),
            selectinload(Flight.airline_rel),
            selectinload(Flight.boarding_passes).selectinload(BoardingPass.passenger),
        ),
    ]


async def list_bookings(
    session: AsyncSession, user_id: str, status_filter: Optional[str] = None
) -> list[Booking]:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    stmt = (
        select(Booking)
        .where(Booking.user_id == uid)
        .options(*_booking_load_options())
        .order_by(Booking.created_at.asc())
    )
    today = date.today()
    if status_filter == "upcoming":
        stmt = stmt.where(Booking.start_date >= today)
    elif status_filter == "completed":
        stmt = stmt.where(Booking.end_date < today)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_booking(
    session: AsyncSession, user_id: str, booking_id: str
) -> Optional[Booking]:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    bid = uuid.UUID(booking_id) if isinstance(booking_id, str) else booking_id
    result = await session.execute(
        select(Booking)
        .where(Booking.id == bid, Booking.user_id == uid)
        .options(*_booking_load_options())
    )
    return result.scalar_one_or_none()


async def delete_booking(session: AsyncSession, user_id: str, booking_id: str) -> bool:
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    bid = uuid.UUID(booking_id) if isinstance(booking_id, str) else booking_id
    result = await session.execute(
        delete(Booking).where(Booking.id == bid, Booking.user_id == uid)
    )
    return result.rowcount > 0
