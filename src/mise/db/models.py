"""SQLAlchemy ORM models for all Mise database tables.

Based on the schema defined in docs/ARCHITECTURE_PROPOSAL.md §4.
"""

from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, Index,
)
from sqlalchemy.orm import relationship

from mise.db.database import Base


# ─── Users & Auth ──────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="user")
    meal_plans = relationship("MealPlan", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    shopping_lists = relationship("ShoppingList", back_populates="user")
    inventory = relationship("InventoryItem", back_populates="user")
    budget_entries = relationship("BudgetEntry", back_populates="user")
    cooking_sessions = relationship("CookingSession", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    household_size = Column(Integer, default=1)
    preferred_units = Column(String(10), default="metric")  # "metric" or "imperial"
    currency = Column(String(3), default="EUR")
    weekly_budget = Column(Float, nullable=True)
    cooking_skill = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    max_cook_time_min = Column(Integer, nullable=True)
    language = Column(String(5), default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id})>"


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pref_type = Column(String(30), nullable=False)  # allergy, dislike, liked_cuisine, preferred_store, meal_slot
    pref_value = Column(String(100), nullable=False)
    weight = Column(Float, default=1.0)  # how strongly this preference counts

    # Relationships
    user = relationship("User", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "pref_type", "pref_value", name="uq_user_preference_type_value"),
        Index("ix_user_preferences_user_type", "user_id", "pref_type"),
    )

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id}, {self.pref_type}={self.pref_value})>"


# ─── Recipes ───────────────────────────────────────────────────────────

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(String(100), primary_key=True)  # slug like 'lasagne-bolognese'
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=True)  # URL if from online
    source_site = Column(String(100), nullable=True)  # "allrecipes.com", "varecha.sk", "manual"
    source_type = Column(String(20), default="manual")  # online, import_paste, import_voice
    rating = Column(Float, nullable=True)  # rating from source site
    user_rating = Column(Integer, nullable=True)  # user's own 1-5 rating
    rating_count = Column(Integer, nullable=True)
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    total_time_min = Column(Integer, nullable=True)
    servings = Column(Integer, default=4)
    difficulty = Column(String(20), nullable=True)  # easy, medium, hard
    cuisine = Column(String(50), nullable=True)
    image_url = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)  # JSON array of steps
    is_saved = Column(Boolean, default=True)
    auto_saved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="recipes")
    tags = relationship("RecipeTag", back_populates="recipe", cascade="all, delete-orphan")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Recipe(id='{self.id}', title='{self.title}')>"


class RecipeTag(Base):
    __tablename__ = "recipe_tags"

    recipe_id = Column(String(100), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    tag = Column(String(50), nullable=False, primary_key=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="tags")

    def __repr__(self):
        return f"<RecipeTag(recipe_id='{self.recipe_id}', tag='{self.tag}')>"


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(String(100), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # canonical: "ground beef"
    quantity = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)  # original unit from recipe
    quantity_metric = Column(Float, nullable=True)  # converted to metric
    unit_metric = Column(String(10), nullable=True)  # "g" or "ml"
    quantity_imperial = Column(Float, nullable=True)  # converted to imperial
    unit_imperial = Column(String(10), nullable=True)  # "oz" or "fl oz"
    category = Column(String(30), nullable=True)  # Meat, Dairy, Produce, Pantry
    is_optional = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")

    def __repr__(self):
        return f"<RecipeIngredient(name='{self.name}', recipe_id='{self.recipe_id}')>"


# ─── Meal Planning ─────────────────────────────────────────────────────

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)  # ISO date
    meal_type = Column(String(20), nullable=False)  # breakfast, lunch, dinner, brunch, morning_snack, afternoon_snack
    recipe_id = Column(String(100), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    servings = Column(Integer, nullable=True)
    status = Column(String(20), default="planned")  # planned, shopped, cooked, skipped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="meal_plans")
    recipe = relationship("Recipe")

    __table_args__ = (
        Index("ix_meal_plans_user_date", "user_id", "date"),
    )

    def __repr__(self):
        return f"<MealPlan(user_id={self.user_id}, date={self.date}, meal_type='{self.meal_type}')>"


# ─── Feedback ───────────────────────────────────────────────────────────

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(100), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    meal_date = Column(Date, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    would_repeat = Column(Boolean, nullable=True)
    modifications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="feedback")
    recipe = relationship("Recipe")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
    )

    def __repr__(self):
        return f"<Feedback(user_id={self.user_id}, rating={self.rating})>"


# ─── Shopping Lists ─────────────────────────────────────────────────────

class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    status = Column(String(20), default="pending")  # pending, in_progress, completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="shopping_lists")
    items = relationship("ShoppingItem", back_populates="list", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ShoppingList(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    list_id = Column(Integer, ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False)
    ingredient_name = Column(String(100), nullable=False)
    quantity_needed = Column(Float, nullable=True)
    unit_needed = Column(String(30), nullable=True)
    in_pantry = Column(Boolean, default=False)
    checked = Column(Boolean, default=False)  # whether purchased
    has_discount = Column(Boolean, default=False)
    best_store = Column(String(50), nullable=True)  # store with best discount
    discount_price = Column(Float, nullable=True)
    discount_percent = Column(Integer, nullable=True)
    discount_valid_until = Column(Date, nullable=True)

    # Relationships
    list = relationship("ShoppingList", back_populates="items")

    def __repr__(self):
        return f"<ShoppingItem(name='{self.ingredient_name}', list_id={self.list_id})>"


# ─── Inventory (Pantry + Due Dates) ────────────────────────────────────

class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(30), nullable=True)  # Dairy, Meat, Produce, Pantry, Frozen
    quantity = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)  # "1L", "500g", "1 bag"
    purchase_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)  # when it expires
    store = Column(String(50), nullable=True)  # where bought
    price = Column(Float, nullable=True)
    source = Column(String(20), default="manual")  # manual, receipt_ocr, voice, shopping_checkoff
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="inventory")

    __table_args__ = (
        Index("ix_inventory_user_due_date", "user_id", "due_date"),
    )

    def __repr__(self):
        return f"<InventoryItem(name='{self.name}', user_id={self.user_id})>"


# ─── Budget ─────────────────────────────────────────────────────────────

class BudgetEntry(Base):
    __tablename__ = "budget_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    store = Column(String(50), nullable=True)
    total_spent = Column(Float, nullable=True)
    planned = Column(Boolean, default=False)  # was this from a mise shopping list?
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="budget_entries")

    def __repr__(self):
        return f"<BudgetEntry(user_id={self.user_id}, date={self.date}, spent={self.total_spent})>"


# ─── Cooking Sessions ───────────────────────────────────────────────────

class CookingSession(Base):
    __tablename__ = "cooking_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(100), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    cooked_date = Column(Date, nullable=False)
    portions = Column(Integer, nullable=True)
    scale_factor = Column(Float, nullable=True)
    smart_scaled = Column(Boolean, default=False)
    ai_adjusted = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)  # 1-5
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="cooking_sessions")
    recipe = relationship("Recipe")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_cooking_session_rating_range"),
    )

    def __repr__(self):
        return f"<CookingSession(user_id={self.user_id}, recipe_id='{self.recipe_id}')>"


# ─── Email Verification ────────────────────────────────────────────────

class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(8), nullable=False)  # 8-digit verification code
    email = Column(String(255), nullable=False)  # the email being verified
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("ix_email_verifications_user_code", "user_id", "code"),
    )

    def __repr__(self):
        return f"<EmailVerification(user_id={self.user_id}, code='{self.code}', used={self.is_used})>"


# ─── Discounts (existing, kept as-is) ──────────────────────────────────

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store = Column(String(50), nullable=False)
    product = Column(String(255), nullable=False)
    category = Column(String(50), nullable=True)
    original_price = Column(Float, nullable=True)
    discount_price = Column(Float, nullable=True)
    discount_percent = Column(Integer, nullable=True)
    valid_until = Column(Date, nullable=True)
    url = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Discount(id={self.id}, store='{self.store}', product='{self.product}')>"