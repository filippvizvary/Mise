"""CRUD operations for Mise database."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from mise.db.models import (
    User, UserProfile, UserPreference, Discount,
    MealPlan, InventoryItem,
)


# ─── Discounts (existing functionality) ─────────────────────────────────

def insert_discounts(session: Session, discounts: list) -> None:
    """Insert a list of discount dicts or DiscountItem objects into the database.

    Each item can be a dict with keys: store, product, category, original_price, discount_price
    Optional keys: discount_percent, valid_until, url
    Or a :class:`mise.scraper.base.DiscountItem` instance.
    """
    for d in discounts:
        # If it's a Pydantic model (DiscountItem), convert to dict
        if hasattr(d, "model_dump"):
            data = d.model_dump()
        else:
            data = dict(d)

        discount = Discount(
            store=data.get("store"),
            product=data.get("product"),
            category=data.get("category"),
            original_price=data.get("original_price"),
            discount_price=data.get("discount_price"),
            discount_percent=data.get("discount_percent"),
            valid_until=data.get("valid_until"),
            url=data.get("url"),
        )
        session.add(discount)
    session.commit()


def get_discounts(
    session: Session,
    store: Optional[str] = None,
    category: Optional[str] = None,
) -> list[Discount]:
    """Query discounts with optional filters. Returns a list of Discount ORM objects."""
    query = session.query(Discount)
    if store is not None:
        query = query.filter(Discount.store == store)
    if category is not None:
        query = query.filter(Discount.category == category)
    return query.all()


# ─── User Auth ──────────────────────────────────────────────────────────

def create_user(
    session: Session,
    username: str,
    email: str,
    password_hash: str,
) -> User:
    """Create a new user with a default profile."""
    user = User(username=username, email=email, password_hash=password_hash)
    session.add(user)
    session.flush()  # get user.id

    # Create default profile
    profile = UserProfile(user_id=user.id)
    session.add(profile)
    session.commit()
    return user


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Look up a user by username."""
    return session.query(User).filter(User.username == username).first()


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Look up a user by email."""
    return session.query(User).filter(User.email == email).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Look up a user by ID."""
    return session.query(User).filter(User.id == user_id).first()


# ─── User Profile ──────────────────────────────────────────────────────

def get_or_create_profile(session: Session, user_id: int) -> UserProfile:
    """Get the user's profile, creating one if it doesn't exist."""
    profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        session.commit()
    return profile


# Fields that can be explicitly set to None (e.g., clearing weekly_budget)
_PROFILE_NULLABLE_FIELDS = {"weekly_budget", "max_cook_time_min"}


def update_profile(session: Session, user_id: int, **kwargs) -> UserProfile:
    """Update profile fields for a user.

    Pass None for fields in _PROFILE_NULLABLE_FIELDS to explicitly clear them.
    For other fields, None values are ignored.
    """
    profile = get_or_create_profile(session, user_id)
    for key, value in kwargs.items():
        if hasattr(profile, key):
            if value is not None or key in _PROFILE_NULLABLE_FIELDS:
                setattr(profile, key, value)
    session.commit()
    return profile


# ─── User Preferences ───────────────────────────────────────────────────

def add_preference(session: Session, user_id: int, pref_type: str, pref_value: str, weight: float = 1.0) -> UserPreference:
    """Add a preference for a user.

    If the exact same (user_id, pref_type, pref_value) already exists,
    returns the existing preference instead of creating a duplicate.
    """
    existing = (
        session.query(UserPreference)
        .filter(
            UserPreference.user_id == user_id,
            UserPreference.pref_type == pref_type,
            UserPreference.pref_value == pref_value,
        )
        .first()
    )
    if existing:
        return existing
    pref = UserPreference(user_id=user_id, pref_type=pref_type, pref_value=pref_value, weight=weight)
    session.add(pref)
    session.commit()
    return pref


def remove_preference(session: Session, user_id: int, pref_type: str, pref_value: str) -> bool:
    """Remove a specific preference. Returns True if found and deleted."""
    pref = (
        session.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.pref_type == pref_type, UserPreference.pref_value == pref_value)
        .first()
    )
    if pref:
        session.delete(pref)
        session.commit()
        return True
    return False


def get_preferences(session: Session, user_id: int, pref_type: Optional[str] = None) -> list[UserPreference]:
    """Get preferences for a user, optionally filtered by type."""
    query = session.query(UserPreference).filter(UserPreference.user_id == user_id)
    if pref_type:
        query = query.filter(UserPreference.pref_type == pref_type)
    return query.all()


# ─── Meal Plans ──────────────────────────────────────────────────────────

def create_meal_plan(
    session: Session,
    user_id: int,
    date: date,
    meal_type: str,
    recipe_id: Optional[str] = None,
    servings: Optional[int] = None,
    status: str = "planned",
) -> MealPlan:
    """Create a new meal plan entry."""
    plan = MealPlan(
        user_id=user_id,
        date=date,
        meal_type=meal_type,
        recipe_id=recipe_id,
        servings=servings,
        status=status,
    )
    session.add(plan)
    session.commit()
    return plan


def get_meal_plans(
    session: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[MealPlan]:
    """Get meal plans for a user, optionally filtered by date range."""
    query = session.query(MealPlan).filter(MealPlan.user_id == user_id)
    if start_date is not None:
        query = query.filter(MealPlan.date >= start_date)
    if end_date is not None:
        query = query.filter(MealPlan.date <= end_date)
    return query.order_by(MealPlan.date, MealPlan.meal_type).all()


def get_meal_plan_by_slot(
    session: Session,
    user_id: int,
    date: date,
    meal_type: str,
) -> Optional[MealPlan]:
    """Get a meal plan for a specific user/date/meal_type slot."""
    return (
        session.query(MealPlan)
        .filter(
            MealPlan.user_id == user_id,
            MealPlan.date == date,
            MealPlan.meal_type == meal_type,
        )
        .first()
    )


def update_meal_plan_status(session: Session, plan_id: int, status: str) -> MealPlan:
    """Update the status of a meal plan."""
    plan = session.query(MealPlan).filter(MealPlan.id == plan_id).first()
    if plan is None:
        raise ValueError(f"MealPlan with id {plan_id} not found")
    plan.status = status
    session.commit()
    return plan


def delete_meal_plan(session: Session, plan_id: int) -> bool:
    """Delete a single meal plan by ID. Returns True if found and deleted."""
    plan = session.query(MealPlan).filter(MealPlan.id == plan_id).first()
    if plan:
        session.delete(plan)
        session.commit()
        return True
    return False


def clear_meal_plans(
    session: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> int:
    """Delete all meal plans for a user in a date range. Returns count deleted."""
    query = session.query(MealPlan).filter(MealPlan.user_id == user_id)
    if start_date is not None:
        query = query.filter(MealPlan.date >= start_date)
    if end_date is not None:
        query = query.filter(MealPlan.date <= end_date)
    count = query.count()
    query.delete(synchronize_session=False)
    session.commit()
    return count


# ─── Inventory ───────────────────────────────────────────────────────────

def get_user_inventory(session: Session, user_id: int) -> list[InventoryItem]:
    """Get all inventory items for a user."""
    return (
        session.query(InventoryItem)
        .filter(InventoryItem.user_id == user_id)
        .order_by(InventoryItem.category, InventoryItem.name)
        .all()
    )


# ─── Discounts (filtered by stores) ─────────────────────────────────────

def get_discounts_for_stores(
    session: Session,
    stores: list[str],
) -> list[Discount]:
    """Get discounts available at the specified stores."""
    return (
        session.query(Discount)
        .filter(Discount.store.in_(stores))
        .order_by(Discount.category, Discount.product)
        .all()
    )


# ─── Feedback ────────────────────────────────────────────────────────────

def get_user_feedback(
    session: Session,
    user_id: int,
    limit: int = 20,
) -> list:
    """Get recent feedback for a user. Returns Feedback ORM objects."""
    from mise.db.models import Feedback
    return (
        session.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )


# ─── Shopping List Items ─────────────────────────────────────────────────

def get_user_shopping_items(
    session: Session,
    user_id: int,
) -> list:
    """Get all unchecked shopping list items for a user. Returns ShoppingItem ORM objects."""
    from mise.db.models import ShoppingList, ShoppingItem
    return (
        session.query(ShoppingItem)
        .join(ShoppingList, ShoppingItem.list_id == ShoppingList.id)
        .filter(
            ShoppingList.user_id == user_id,
            ShoppingItem.checked.is_(False),
        )
        .order_by(ShoppingItem.ingredient_name)
        .all()
    )
