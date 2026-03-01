"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('oauth_google_id', sa.String(), nullable=True),
        sa.Column('oauth_github_id', sa.String(), nullable=True),
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('two_factor_secret', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_oauth_google_id'), 'users', ['oauth_google_id'], unique=True)
    op.create_index(op.f('ix_users_oauth_github_id'), 'users', ['oauth_github_id'], unique=True)

    # Health profiles table
    op.create_table(
        'health_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('occupation_type', sa.String(), nullable=True),
        sa.Column('activity_level', sa.String(), nullable=True),
        sa.Column('dietary_preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dietary_restrictions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fitness_goals', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('initial_assessment', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('privacy_settings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Health metrics table
    op.create_table(
        'health_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('bmi', sa.Float(), nullable=True),
        sa.Column('wellness_score', sa.Float(), nullable=True),
        sa.Column('activity_frequency', sa.Integer(), nullable=True),
        sa.Column('activity_duration', sa.String(), nullable=True),
        sa.Column('goal_progress', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_health_metrics_user_id'), 'health_metrics', ['user_id'], unique=False)

    # AI insights table
    op.create_table(
        'ai_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('insight_type', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('context_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_insights_user_id'), 'ai_insights', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_insights_user_id'), table_name='ai_insights')
    op.drop_table('ai_insights')
    op.drop_index(op.f('ix_health_metrics_user_id'), table_name='health_metrics')
    op.drop_table('health_metrics')
    op.drop_table('health_profiles')
    op.drop_index(op.f('ix_users_oauth_github_id'), table_name='users')
    op.drop_index(op.f('ix_users_oauth_google_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
