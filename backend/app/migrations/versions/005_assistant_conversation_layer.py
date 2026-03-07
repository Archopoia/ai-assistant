"""Add assistant conversation and message persistence

Revision ID: 005_assistant_conversation_layer
Revises: 004_meal_planning_foundation
Create Date: 2026-03-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_assistant_conversation_layer"
down_revision = "004_meal_planning_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("response_mode", sa.String(), nullable=False, server_default=sa.text("'concise'")),
        sa.Column("topic_hint", sa.String(), nullable=True),
        sa.Column("compressed_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assistant_conversations_id"), "assistant_conversations", ["id"], unique=False)
    op.create_index(op.f("ix_assistant_conversations_user_id"), "assistant_conversations", ["user_id"], unique=False)

    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assistant_messages_id"), "assistant_messages", ["id"], unique=False)
    op.create_index(op.f("ix_assistant_messages_conversation_id"), "assistant_messages", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assistant_messages_conversation_id"), table_name="assistant_messages")
    op.drop_index(op.f("ix_assistant_messages_id"), table_name="assistant_messages")
    op.drop_table("assistant_messages")

    op.drop_index(op.f("ix_assistant_conversations_user_id"), table_name="assistant_conversations")
    op.drop_index(op.f("ix_assistant_conversations_id"), table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
