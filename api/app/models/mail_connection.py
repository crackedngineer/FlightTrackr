import uuid
from sqlalchemy import String, Text, DateTime, func, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class UserMailConnection(Base, TimestampMixin):
    __tablename__ = "user_mail_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_email", name="uq_mail_connections_user_provider_email"),
        Index("ix_mail_connections_user_id", "user_id"),
        Index("ix_mail_connections_user_status", "user_id", "status"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_tokens: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    connected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_synced_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
