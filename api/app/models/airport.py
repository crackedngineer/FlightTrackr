import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column
from app.db.base import Base, TimestampMixin


class Airport(Base, TimestampMixin):
    __tablename__ = "airports"
    __table_args__ = ({"schema": "public"},)

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    iata_code = mapped_column(String(10), nullable=False)
    icao_code = mapped_column(String(10), nullable=True, unique=True)
    name = mapped_column(String(100), nullable=False)
    city = mapped_column(String(50), nullable=True)
    country = mapped_column(String(50), nullable=True)
    latitude = mapped_column(Numeric(9, 6), nullable=True)
    longitude = mapped_column(Numeric(9, 6), nullable=True)
    timezone = mapped_column(String(50), nullable=True)