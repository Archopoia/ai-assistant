"""Add auth token fields for verification/reset

Revision ID: 002_auth_token_fields
Revises: 001_initial
Create Date: 2026-03-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_auth_token_fields"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_reset_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(
        op.f("ix_users_email_verification_token_hash"),
        "users",
        ["email_verification_token_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_password_reset_token_hash"),
        "users",
        ["password_reset_token_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_password_reset_token_hash"), table_name="users")
    op.drop_index(op.f("ix_users_email_verification_token_hash"), table_name="users")

    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
