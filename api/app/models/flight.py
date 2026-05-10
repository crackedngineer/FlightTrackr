import uuid
from typing import Optional
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.models.airline import Airline
from app.models.airport import Airport


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "airline_id", "pnr_code", name="uq_bookings_user_airline_pnr"
        ),
        Index("ix_bookings_user_start_date", "user_id", "start_date"),
        {"schema": "public"},
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    pnr_code = mapped_column(String(20), nullable=False, index=True)
    source = mapped_column(String(20), nullable=False, default="gmail")
    document_url = mapped_column(String(500), nullable=True)
    airline_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"), nullable=False)
    booking_type = mapped_column(String(20), nullable=False, default="direct")
    start_date = mapped_column(Date, nullable=True)
    end_date = mapped_column(Date, nullable=True)

    flights: Mapped[list["Flight"]] = relationship(
        "Flight", back_populates="booking", order_by="Flight.departure_time"
    )
    passengers: Mapped[list["Passenger"]] = relationship(
        "Passenger", back_populates="booking"
    )
    airline_rel: Mapped[Optional["Airline"]] = relationship(
        "Airline", foreign_keys="[Booking.airline_id]"
    )


class Flight(Base, TimestampMixin):
    __tablename__ = "flights"
    __table_args__ = (
        Index("ix_flights_booking_dep_time", "booking_id", "departure_time"),
        Index("ix_flights_departure_airport", "departure_airport"),
        Index("ix_flights_arrival_airport", "arrival_airport"),
        Index("ix_flights_airline_id", "airline_id"),
        Index("ix_flights_status", "status"),
        CheckConstraint(
            "status IN ('upcoming','completed','cancelled')", name="ck_flights_status"
        ),
        UniqueConstraint(
            "booking_id",
            "flight_number",
            "airline_id",
            "departure_time",
            name="uq_flights_booking_flight_dep",
        ),
        {"schema": "public"},
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False
    )
    flight_number = mapped_column(String(20), nullable=False)
    airline_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"), nullable=False)
    departure_airport = mapped_column(
        UUID(as_uuid=True), ForeignKey("airports.id"), nullable=False
    )
    arrival_airport = mapped_column(
        UUID(as_uuid=True), ForeignKey("airports.id"), nullable=False
    )
    departure_time = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_time = mapped_column(DateTime(timezone=True), nullable=True)
    gate = mapped_column(String(10))
    terminal = mapped_column(String(10))
    status = mapped_column(String(20), nullable=False, default="upcoming")

    booking: Mapped["Booking"] = relationship("Booking", back_populates="flights")
    airline_rel: Mapped[Optional["Airline"]] = relationship(
        "Airline", foreign_keys="[Flight.airline_id]"
    )
    dep_airport: Mapped[Optional["Airport"]] = relationship(
        "Airport", foreign_keys="[Flight.departure_airport]"
    )
    arr_airport: Mapped[Optional["Airport"]] = relationship(
        "Airport", foreign_keys="[Flight.arrival_airport]"
    )
    boarding_passes: Mapped[list["BoardingPass"]] = relationship(
        "BoardingPass", back_populates="flight"
    )


class Passenger(Base, TimestampMixin):
    __tablename__ = "passengers"
    __table_args__ = (
        UniqueConstraint(
            "booking_id", "first_name", "last_name", name="uq_passengers_booking_name"
        ),
        {"schema": "public"},
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True
    )
    first_name = mapped_column(String(100), nullable=False)
    last_name = mapped_column(String(100), nullable=False)

    booking: Mapped["Booking"] = relationship("Booking", back_populates="passengers")
    boarding_passes: Mapped[list["BoardingPass"]] = relationship(
        "BoardingPass", back_populates="passenger"
    )


class BoardingPass(Base, TimestampMixin):
    __tablename__ = "boarding_passes"
    __table_args__ = (
        UniqueConstraint(
            "flight_id", "passenger_id", name="uq_boarding_passes_flight_passenger"
        ),
        UniqueConstraint("barcode", name="uq_boarding_passes_barcode"),
        {"schema": "public"},
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False, index=True
    )
    passenger_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("passengers.id"), nullable=False, index=True
    )
    barcode = mapped_column(String(500), nullable=False)
    seat_number = mapped_column(String(10))
    cabin_class = mapped_column(String(10))
    boarding_group = mapped_column(String(10))
    source = mapped_column(String(20), nullable=True)
    source_message_id = mapped_column(String(100), nullable=True)

    flight: Mapped["Flight"] = relationship("Flight", back_populates="boarding_passes")
    passenger: Mapped["Passenger"] = relationship(
        "Passenger", back_populates="boarding_passes"
    )
