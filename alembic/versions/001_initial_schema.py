"""Initial schema – all tables from §4.

Revision ID: 001
Revises: None
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Users & Auth ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("household_size", sa.Integer(), nullable=True),
        sa.Column("preferred_units", sa.String(length=10), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("weekly_budget", sa.Float(), nullable=True),
        sa.Column("cooking_skill", sa.String(length=20), nullable=True),
        sa.Column("max_cook_time_min", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pref_type", sa.String(length=30), nullable=False),
        sa.Column("pref_value", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "pref_type", "pref_value", name="uq_user_preference_type_value"),
    )
    op.create_index("ix_user_preferences_user_type", "user_preferences", ["user_id", "pref_type"])

    # ─── Email Verification ────────────────────────────────────────────
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_verifications_user_code", "email_verifications", ["user_id", "code"])

    # ─── Recipes ───────────────────────────────────────────────────────
    op.create_table(
        "recipes",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_site", sa.String(length=100), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("user_rating", sa.Integer(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), nullable=True),
        sa.Column("cook_time_min", sa.Integer(), nullable=True),
        sa.Column("total_time_min", sa.Integer(), nullable=True),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("cuisine", sa.String(length=50), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_saved", sa.Boolean(), nullable=True),
        sa.Column("auto_saved", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "recipe_tags",
        sa.Column("recipe_id", sa.String(length=100), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "tag"),
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("quantity_metric", sa.Float(), nullable=True),
        sa.Column("unit_metric", sa.String(length=10), nullable=True),
        sa.Column("quantity_imperial", sa.Float(), nullable=True),
        sa.Column("unit_imperial", sa.String(length=10), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("is_optional", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── Meal Planning ─────────────────────────────────────────────────
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=20), nullable=False),
        sa.Column("recipe_id", sa.String(length=100), nullable=True),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_plans_user_date", "meal_plans", ["user_id", "date"])

    # ─── Feedback ──────────────────────────────────────────────────────
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.String(length=100), nullable=True),
        sa.Column("meal_date", sa.Date(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("would_repeat", sa.Boolean(), nullable=True),
        sa.Column("modifications", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
    )

    # ─── Shopping Lists ────────────────────────────────────────────────
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date_range_start", sa.Date(), nullable=True),
        sa.Column("date_range_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shopping_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_name", sa.String(length=100), nullable=False),
        sa.Column("quantity_needed", sa.Float(), nullable=True),
        sa.Column("unit_needed", sa.String(length=30), nullable=True),
        sa.Column("in_pantry", sa.Boolean(), nullable=True),
        sa.Column("checked", sa.Boolean(), nullable=True),
        sa.Column("has_discount", sa.Boolean(), nullable=True),
        sa.Column("best_store", sa.String(length=50), nullable=True),
        sa.Column("discount_price", sa.Float(), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("discount_valid_until", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── Inventory ─────────────────────────────────────────────────────
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("store", sa.String(length=50), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_user_due_date", "inventory", ["user_id", "due_date"])

    # ─── Budget ─────────────────────────────────────────────────────────
    op.create_table(
        "budget_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("store", sa.String(length=50), nullable=True),
        sa.Column("total_spent", sa.Float(), nullable=True),
        sa.Column("planned", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── Cooking Sessions ──────────────────────────────────────────────
    op.create_table(
        "cooking_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.String(length=100), nullable=False),
        sa.Column("cooked_date", sa.Date(), nullable=False),
        sa.Column("portions", sa.Integer(), nullable=True),
        sa.Column("scale_factor", sa.Float(), nullable=True),
        sa.Column("smart_scaled", sa.Boolean(), nullable=True),
        sa.Column("ai_adjusted", sa.Boolean(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_cooking_session_rating_range"),
    )

    # ─── Discounts (existing) ──────────────────────────────────────────
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store", sa.String(length=50), nullable=False),
        sa.Column("product", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("original_price", sa.Float(), nullable=True),
        sa.Column("discount_price", sa.Float(), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("discounts")
    op.drop_table("cooking_sessions")
    op.drop_table("budget_entries")
    op.drop_table("inventory")
    op.drop_table("shopping_items")
    op.drop_table("shopping_lists")
    op.drop_table("feedback")
    op.drop_table("meal_plans")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipe_tags")
    op.drop_table("recipes")
    op.drop_index("ix_email_verifications_user_code", table_name="email_verifications")
    op.drop_table("email_verifications")
    op.drop_index("ix_user_preferences_user_type", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_table("user_profile")
    op.drop_table("users")
