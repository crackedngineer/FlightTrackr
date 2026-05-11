"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. airlines (integer PK — referenced by bookings and flights)
    op.create_table(
        "airlines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("iata_code", sa.String(10), nullable=False),
        sa.Column("icao_code", sa.String(10), nullable=True),
        sa.Column("alias", sa.String(100), nullable=True),
        sa.Column("callsign", sa.String(50), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("icao_code", name="uq_airlines_icao_code"),
        schema="public",
    )

    # 2. airports (UUID PK — referenced by flights as departure/arrival)
    op.create_table(
        "airports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("iata_code", sa.String(10), nullable=False),
        sa.Column("icao_code", sa.String(10), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("city", sa.String(50), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("icao_code", name="uq_airports_icao_code"),
        schema="public",
    )

    # 3. user_oauth_tokens
    op.create_table(
        "user_oauth_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="google"),
        sa.Column("refresh_token", sa.String(2048), nullable=False),
        sa.Column("access_token", sa.String(2048), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_oauth_tokens_user_provider"),
        schema="public",
    )
    op.create_index("ix_user_oauth_tokens_user_id", "user_oauth_tokens", ["user_id"], schema="public")

    # 4. gmail_sync_jobs
    op.create_table(
        "gmail_sync_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("emails_scanned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passes_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passes_saved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_gmail_sync_jobs_user_id", "gmail_sync_jobs", ["user_id"], schema="public")

    # 5. bookings (was "trips" in old migrations — model uses "bookings")
    op.create_table(
        "bookings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pnr_code", sa.String(20), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="gmail"),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("airline_id", sa.Integer, nullable=False),
        sa.Column("booking_type", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["airline_id"], ["public.airlines.id"]),
        sa.UniqueConstraint("user_id", "airline_id", "pnr_code", name="uq_bookings_user_airline_pnr"),
        schema="public",
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], schema="public")
    op.create_index("ix_bookings_pnr_code", "bookings", ["pnr_code"], schema="public")
    op.create_index("ix_bookings_user_start_date", "bookings", ["user_id", "start_date"], schema="public")

    # 6. flights (normalized — uses booking_id, not trip_id)
    op.create_table(
        "flights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("flight_number", sa.String(20), nullable=False),
        sa.Column("airline_id", sa.Integer, nullable=False),
        sa.Column("departure_airport", UUID(as_uuid=True), nullable=False),
        sa.Column("arrival_airport", UUID(as_uuid=True), nullable=False),
        sa.Column("departure_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gate", sa.String(10), nullable=True),
        sa.Column("terminal", sa.String(10), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="upcoming"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["booking_id"], ["public.bookings.id"]),
        sa.ForeignKeyConstraint(["airline_id"], ["public.airlines.id"]),
        sa.ForeignKeyConstraint(["departure_airport"], ["public.airports.id"]),
        sa.ForeignKeyConstraint(["arrival_airport"], ["public.airports.id"]),
        sa.CheckConstraint("status IN ('upcoming','completed','cancelled')", name="ck_flights_status"),
        sa.UniqueConstraint(
            "booking_id", "flight_number", "airline_id", "departure_time",
            name="uq_flights_booking_flight_dep",
        ),
        schema="public",
    )
    op.create_index("ix_flights_booking_dep_time", "flights", ["booking_id", "departure_time"], schema="public")
    op.create_index("ix_flights_departure_airport", "flights", ["departure_airport"], schema="public")
    op.create_index("ix_flights_arrival_airport", "flights", ["arrival_airport"], schema="public")
    op.create_index("ix_flights_airline_id", "flights", ["airline_id"], schema="public")
    op.create_index("ix_flights_status", "flights", ["status"], schema="public")

    # 7. passengers
    op.create_table(
        "passengers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["booking_id"], ["public.bookings.id"]),
        sa.UniqueConstraint("booking_id", "first_name", "last_name", name="uq_passengers_booking_name"),
        schema="public",
    )
    op.create_index("ix_passengers_booking_id", "passengers", ["booking_id"], schema="public")

    # 8. boarding_passes (no timestamps — BoardingPass model has no TimestampMixin)
    op.create_table(
        "boarding_passes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flight_id", UUID(as_uuid=True), nullable=False),
        sa.Column("passenger_id", UUID(as_uuid=True), nullable=False),
        sa.Column("barcode", sa.String(500), nullable=False),
        sa.Column("seat_number", sa.String(10), nullable=True),
        sa.Column("cabin_class", sa.String(10), nullable=True),
        sa.Column("boarding_group", sa.String(10), nullable=True),
        sa.Column("source", sa.String(20), nullable=True),
        sa.Column("source_message_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["flight_id"], ["public.flights.id"]),
        sa.ForeignKeyConstraint(["passenger_id"], ["public.passengers.id"]),
        sa.UniqueConstraint("flight_id", "passenger_id", name="uq_boarding_passes_flight_passenger"),
        sa.UniqueConstraint("barcode", name="uq_boarding_passes_barcode"),
        schema="public",
    )
    op.create_index("ix_boarding_passes_flight_id", "boarding_passes", ["flight_id"], schema="public")
    op.create_index("ix_boarding_passes_passenger_id", "boarding_passes", ["passenger_id"], schema="public")


def downgrade() -> None:
    op.drop_table("boarding_passes", schema="public")
    op.drop_table("passengers", schema="public")
    op.drop_table("flights", schema="public")
    op.drop_table("bookings", schema="public")
    op.drop_table("gmail_sync_jobs", schema="public")
    op.drop_table("user_oauth_tokens", schema="public")
    op.drop_table("airports", schema="public")
    op.drop_table("airlines", schema="public")
