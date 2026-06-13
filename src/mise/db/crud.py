"""CRUD operations for Mise database."""

from typing import Optional

from sqlalchemy.orm import Session

from mise.db.models import (
    User, UserProfile, UserPreference, Discount,
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


def update_profile(session: Session, user_id: int, **kwargs) -> UserProfile:
    """Update profile fields for a user."""
    profile = get_or_create_profile(session, user_id)
    for key, value in kwargs.items():
        if hasattr(profile, key) and value is not None:
            setattr(profile, key, value)
    session.commit()
    return profile


# ─── User Preferences ───────────────────────────────────────────────────

def add_preference(session: Session, user_id: int, pref_type: str, pref_value: str, weight: float = 1.0) -> UserPreference:
    """Add a preference for a user."""
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