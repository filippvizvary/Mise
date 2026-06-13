"""User profile management."""

from mise.db.database import SessionLocal
from mise.db.crud import get_or_create_profile as crud_get_or_create_profile, update_profile as crud_update_profile
from mise.db.models import UserProfile


def get_profile(user_id: int) -> UserProfile:
    """Get a user's profile, creating one with defaults if it doesn't exist."""
    session = SessionLocal()
    try:
        return crud_get_or_create_profile(session, user_id)
    finally:
        session.close()


def update_profile(user_id: int, **kwargs) -> UserProfile:
    """Update a user's profile fields.

    Accepted kwargs: household_size, preferred_units, currency,
    weekly_budget, cooking_skill, max_cook_time_min, language
    """
    session = SessionLocal()
    try:
        profile = crud_update_profile(session, user_id, **kwargs)
        return profile
    finally:
        session.close()