"""Database management for Mise."""

from mise.db.database import Base, SessionLocal, engine, get_db, init_db
from mise.db.models import (
    User, UserProfile, UserPreference,
    Recipe, RecipeTag, RecipeIngredient,
    MealPlan, Feedback,
    ShoppingList, ShoppingItem,
    InventoryItem, BudgetEntry, CookingSession,
    EmailVerification,
    Discount,
)
from mise.db.crud import (
    insert_discounts, get_discounts,
    create_user, get_user_by_username, get_user_by_email, get_user_by_id,
    get_or_create_profile, update_profile,
    add_preference, remove_preference, get_preferences,
)

__all__ = [
    # Database
    "Base", "SessionLocal", "engine", "get_db", "init_db",
    # Models
    "User", "UserProfile", "UserPreference",
    "Recipe", "RecipeTag", "RecipeIngredient",
    "MealPlan", "Feedback",
    "ShoppingList", "ShoppingItem",
    "InventoryItem", "BudgetEntry", "CookingSession",
    "EmailVerification",
    "Discount",
    # CRUD
    "insert_discounts", "get_discounts",
    "create_user", "get_user_by_username", "get_user_by_email", "get_user_by_id",
    "get_or_create_profile", "update_profile",
    "add_preference", "remove_preference", "get_preferences",
]