"""Mise user profile and preferences module."""

from mise.user.profile import get_profile, update_profile
from mise.user.preferences import (
    add_allergy, add_dislike, add_liked_cuisine, add_preferred_store, add_meal_slot,
    remove_allergy, remove_dislike, remove_liked_cuisine, remove_preferred_store, remove_meal_slot,
    list_preferences,
)

__all__ = [
    "get_profile", "update_profile",
    "add_allergy", "add_dislike", "add_liked_cuisine", "add_preferred_store", "add_meal_slot",
    "remove_allergy", "remove_dislike", "remove_liked_cuisine", "remove_preferred_store", "remove_meal_slot",
    "list_preferences",
]