from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class Airline(Base, TimestampMixin):
    __tablename__ = "airlines"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[int] = mapped_column(primary_key=True)
    name = mapped_column(String(100), nullable=False)
    airline_code = mapped_column(String(10), nullable=True)
    iata_code = mapped_column(String(10), nullable=False)
    icao_code = mapped_column(String(10), nullable=True, unique=True)
    alias = mapped_column(String(100), nullable=True)
    callsign = mapped_column(String(50), nullable=True)
    country = mapped_column(String(50), nullable=True)
    website = mapped_column(String(255), nullable=True)
    active = mapped_column(Boolean, nullable=False, default=True)
