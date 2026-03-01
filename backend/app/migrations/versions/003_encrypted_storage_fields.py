"""Add encrypted storage fields for health data

Revision ID: 003_encrypted_storage_fields
Revises: 002_auth_token_fields
Create Date: 2026-03-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "003_encrypted_storage_fields"
down_revision = "002_auth_token_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("health_profiles", sa.Column("encrypted_data", sa.String(), nullable=True))
    op.add_column("health_metrics", sa.Column("encrypted_data", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("health_metrics", "encrypted_data")
    op.drop_column("health_profiles", "encrypted_data")
