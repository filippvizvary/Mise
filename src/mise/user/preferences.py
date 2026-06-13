"""User preference management.

Preference types:
- allergy: Food allergies (e.g., "peanuts", "shellfish")
- dislike: Disliked ingredients (e.g., "olives", "cilantro")
- liked_cuisine: Liked cuisines (e.g., "Italian", "Mexican")
- preferred_store: Preferred stores, ranked (e.g., "Lidl", "Kaufland")
- meal_slot: Which meals to plan (e.g., "breakfast", "lunch", "dinner")
"""

from typing import Optional

from mise.db.database import SessionLocal
from mise.db.crud import add_preference, remove_preference, get_preferences
from mise.db.models import UserPreference


# ─── Convenience functions for each preference type ─────────────────────

def add_allergy(user_id: int, value: str) -> UserPreference:
    """Add an allergy for a user."""
    session = SessionLocal()
    try:
        return add_preference(session, user_id, "allergy", value)
    finally:
        session.close()


def remove_allergy(user_id: int, value: str) -> bool:
    """Remove an allergy for a user."""
    session = SessionLocal()
    try:
        return remove_preference(session, user_id, "allergy", value)
    finally:
        session.close()


def add_dislike(user_id: int, value: str) -> UserPreference:
    """Add a disliked ingredient for a user."""
    session = SessionLocal()
    try:
        return add_preference(session, user_id, "dislike", value)
    finally:
        session.close()


def remove_dislike(user_id: int, value: str) -> bool:
    """Remove a disliked ingredient for a user."""
    session = SessionLocal()
    try:
        return remove_preference(session, user_id, "dislike", value)
    finally:
        session.close()


def add_liked_cuisine(user_id: int, value: str) -> UserPreference:
    """Add a liked cuisine for a user."""
    session = SessionLocal()
    try:
        return add_preference(session, user_id, "liked_cuisine", value)
    finally:
        session.close()


def remove_liked_cuisine(user_id: int, value: str) -> bool:
    """Remove a liked cuisine for a user."""
    session = SessionLocal()
    try:
        return remove_preference(session, user_id, "liked_cuisine", value)
    finally:
        session.close()


def add_preferred_store(user_id: int, value: str) -> UserPreference:
    """Add a preferred store for a user."""
    session = SessionLocal()
    try:
        return add_preference(session, user_id, "preferred_store", value)
    finally:
        session.close()


def remove_preferred_store(user_id: int, value: str) -> bool:
    """Remove a preferred store for a user."""
    session = SessionLocal()
    try:
        return remove_preference(session, user_id, "preferred_store", value)
    finally:
        session.close()


def add_meal_slot(user_id: int, value: str) -> UserPreference:
    """Add a meal slot preference for a user."""
    session = SessionLocal()
    try:
        return add_preference(session, user_id, "meal_slot", value)
    finally:
        session.close()


def remove_meal_slot(user_id: int, value: str) -> bool:
    """Remove a meal slot preference for a user."""
    session = SessionLocal()
    try:
        return remove_preference(session, user_id, "meal_slot", value)
    finally:
        session.close()


def list_preferences(user_id: int, pref_type: Optional[str] = None) -> list[UserPreference]:
    """List preferences for a user, optionally filtered by type."""
    session = SessionLocal()
    try:
        return get_preferences(session, user_id, pref_type)
    finally:
        session.close()