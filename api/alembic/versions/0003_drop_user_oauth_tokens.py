"""drop user_oauth_tokens and add missing timestamps to boarding_passes

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop user_oauth_tokens — superseded by user_mail_connections
    op.drop_index("ix_user_oauth_tokens_user_id", table_name="user_oauth_tokens", schema="public")
    op.drop_table("user_oauth_tokens", schema="public")

    # 2. Add created_at / updated_at to boarding_passes
    #    (model has TimestampMixin but 0001 created the table without timestamps)
    op.add_column(
        "boarding_passes",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="public",
    )
    op.add_column(
        "boarding_passes",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="public",
    )


def downgrade() -> None:
    # Reverse timestamp columns
    op.drop_column("boarding_passes", "updated_at", schema="public")
    op.drop_column("boarding_passes", "created_at", schema="public")

    # Recreate user_oauth_tokens
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
