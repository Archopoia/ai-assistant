"""Add meal planning, recipe and nutrition foundation

Revision ID: 004_meal_planning_foundation
Revises: 003_encrypted_storage_fields
Create Date: 2026-03-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_meal_planning_foundation"
down_revision = "003_encrypted_storage_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("health_profiles", sa.Column("allergies_intolerances", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("health_profiles", sa.Column("disliked_ingredients", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("health_profiles", sa.Column("cuisine_preferences", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("health_profiles", sa.Column("calorie_target_kcal", sa.Float(), nullable=True))
    op.add_column("health_profiles", sa.Column("macronutrient_targets", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("health_profiles", sa.Column("meals_per_day", sa.Integer(), nullable=True))
    op.add_column("health_profiles", sa.Column("meal_schedule", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("health_profiles", sa.Column("timezone", sa.String(), nullable=True))

    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("nutrition", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("aliases", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingredients_external_id"), "ingredients", ["external_id"], unique=True)
    op.create_index(op.f("ix_ingredients_id"), "ingredients", ["id"], unique=False)
    op.create_index(op.f("ix_ingredients_label"), "ingredients", ["label"], unique=False)
    op.create_index(op.f("ix_ingredients_category"), "ingredients", ["category"], unique=False)

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("cuisine", sa.String(), nullable=False),
        sa.Column("meal", sa.String(), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("ingredients", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("time", sa.Integer(), nullable=False),
        sa.Column("difficulty_level", sa.String(), nullable=False),
        sa.Column("dietary_tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("img", sa.String(), nullable=True),
        sa.Column("preparation", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("nutrition", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("rating_avg", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipes_external_id"), "recipes", ["external_id"], unique=True)
    op.create_index(op.f("ix_recipes_id"), "recipes", ["id"], unique=False)
    op.create_index(op.f("ix_recipes_title"), "recipes", ["title"], unique=False)
    op.create_index(op.f("ix_recipes_cuisine"), "recipes", ["cuisine"], unique=False)
    op.create_index(op.f("ix_recipes_meal"), "recipes", ["meal"], unique=False)

    op.create_table(
        "meal_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("duration", sa.String(), nullable=False),
        sa.Column("target_date", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("meals", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("alternatives", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("strategy", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("nutritional_balance_score", sa.Float(), nullable=True),
        sa.Column("diversity_index", sa.Float(), nullable=True),
        sa.Column("micronutrient_coverage", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("weekly_trends", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("sustainability_metrics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_plans_id"), "meal_plans", ["id"], unique=False)
    op.create_index(op.f("ix_meal_plans_user_id"), "meal_plans", ["user_id"], unique=False)
    op.create_index(op.f("ix_meal_plans_duration"), "meal_plans", ["duration"], unique=False)
    op.create_index(op.f("ix_meal_plans_target_date"), "meal_plans", ["target_date"], unique=False)

    op.create_table(
        "meal_plan_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meal_plan_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["meal_plans.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_plan_versions_id"), "meal_plan_versions", ["id"], unique=False)
    op.create_index(op.f("ix_meal_plan_versions_meal_plan_id"), "meal_plan_versions", ["meal_plan_id"], unique=False)
    op.create_index(op.f("ix_meal_plan_versions_user_id"), "meal_plan_versions", ["user_id"], unique=False)
    op.create_index(op.f("ix_meal_plan_versions_version"), "meal_plan_versions", ["version"], unique=False)

    op.create_table(
        "nutrition_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("meal_plan_id", sa.Integer(), nullable=True),
        sa.Column("meal_label", sa.String(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calories_kcal", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False),
        sa.Column("carbs_g", sa.Float(), nullable=False),
        sa.Column("fats_g", sa.Float(), nullable=False),
        sa.Column("micronutrients", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["meal_plans.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nutrition_logs_id"), "nutrition_logs", ["id"], unique=False)
    op.create_index(op.f("ix_nutrition_logs_user_id"), "nutrition_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_nutrition_logs_meal_plan_id"), "nutrition_logs", ["meal_plan_id"], unique=False)
    op.create_index(op.f("ix_nutrition_logs_meal_label"), "nutrition_logs", ["meal_label"], unique=False)
    op.create_index(op.f("ix_nutrition_logs_logged_at"), "nutrition_logs", ["logged_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_nutrition_logs_logged_at"), table_name="nutrition_logs")
    op.drop_index(op.f("ix_nutrition_logs_meal_label"), table_name="nutrition_logs")
    op.drop_index(op.f("ix_nutrition_logs_meal_plan_id"), table_name="nutrition_logs")
    op.drop_index(op.f("ix_nutrition_logs_user_id"), table_name="nutrition_logs")
    op.drop_index(op.f("ix_nutrition_logs_id"), table_name="nutrition_logs")
    op.drop_table("nutrition_logs")

    op.drop_index(op.f("ix_meal_plan_versions_version"), table_name="meal_plan_versions")
    op.drop_index(op.f("ix_meal_plan_versions_user_id"), table_name="meal_plan_versions")
    op.drop_index(op.f("ix_meal_plan_versions_meal_plan_id"), table_name="meal_plan_versions")
    op.drop_index(op.f("ix_meal_plan_versions_id"), table_name="meal_plan_versions")
    op.drop_table("meal_plan_versions")

    op.drop_index(op.f("ix_meal_plans_target_date"), table_name="meal_plans")
    op.drop_index(op.f("ix_meal_plans_duration"), table_name="meal_plans")
    op.drop_index(op.f("ix_meal_plans_user_id"), table_name="meal_plans")
    op.drop_index(op.f("ix_meal_plans_id"), table_name="meal_plans")
    op.drop_table("meal_plans")

    op.drop_index(op.f("ix_recipes_meal"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_cuisine"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_title"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_external_id"), table_name="recipes")
    op.drop_table("recipes")

    op.drop_index(op.f("ix_ingredients_category"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_label"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_external_id"), table_name="ingredients")
    op.drop_table("ingredients")

    op.drop_column("health_profiles", "timezone")
    op.drop_column("health_profiles", "meal_schedule")
    op.drop_column("health_profiles", "meals_per_day")
    op.drop_column("health_profiles", "macronutrient_targets")
    op.drop_column("health_profiles", "calorie_target_kcal")
    op.drop_column("health_profiles", "cuisine_preferences")
    op.drop_column("health_profiles", "disliked_ingredients")
    op.drop_column("health_profiles", "allergies_intolerances")
