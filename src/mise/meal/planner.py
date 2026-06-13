"""Core meal planning logic.

Provides functions for planning meals at different time horizons:
- plan_meal(): Plan a single meal slot
- plan_day(): Plan all meal slots for a day
- plan_week(): Plan 7 days of meals
- show_plan(): Display current meal plans
- clear_plan(): Remove meal plans
- update_status(): Change a meal plan's status
"""

import random
from datetime import date, timedelta
from typing import Optional

from mise.db.database import SessionLocal
from mise.db.crud import (
    create_meal_plan,
    get_meal_plans,
    get_meal_plan_by_slot,
    update_meal_plan_status as crud_update_status,
    delete_meal_plan as crud_delete_plan,
    clear_meal_plans as crud_clear_plans,
)
from mise.meal.suggestions import MealType, get_suggestions, MealSuggestion


# ─── Constants ────────────────────────────────────────────────────────────

DEFAULT_MEAL_SLOTS = ["breakfast", "lunch", "dinner"]

VALID_STATUSES = {"planned", "shopped", "cooked", "skipped"}


# ─── Helper ───────────────────────────────────────────────────────────────

def _get_user_meal_slots(user_id: int) -> list[str]:
    """Get the user's configured meal slots, or default to breakfast/lunch/dinner."""
    from mise.user.preferences import list_preferences
    prefs = list_preferences(user_id, pref_type="meal_slot")
    if prefs:
        return [p.pref_value for p in prefs]
    return DEFAULT_MEAL_SLOTS


def _validate_meal_type(meal_type: str) -> str:
    """Validate and normalize a meal type string.

    Raises ValueError if the meal type is not valid.
    Returns the normalized meal type string.
    """
    valid = {m.value for m in MealType}
    if meal_type not in valid:
        raise ValueError(
            f"Invalid meal type '{meal_type}'. "
            f"Valid types: {', '.join(sorted(valid))}"
        )
    return meal_type


def _validate_status(status: str) -> str:
    """Validate a meal plan status.

    Raises ValueError if the status is not valid.
    """
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. "
            f"Valid statuses: {', '.join(sorted(VALID_STATUSES))}"
        )
    return status


# ─── Plan a single meal ───────────────────────────────────────────────────

def plan_meal(
    user_id: int,
    target_date: date,
    meal_type: str,
    recipe_id: Optional[str] = None,
    servings: Optional[int] = None,
) -> dict:
    """Plan a single meal slot.

    If recipe_id is provided, creates the plan directly.
    If not, this is a placeholder — the CLI should call get_suggestions()
    first to let the user pick.

    Args:
        user_id: The user ID
        target_date: Which day
        meal_type: breakfast, lunch, dinner, brunch, morning_snack, afternoon_snack
        recipe_id: Optional recipe to assign
        servings: Optional number of servings

    Returns:
        Dict with plan details
    """
    meal_type = _validate_meal_type(meal_type)

    session = SessionLocal()
    try:
        # Check for existing plan at this slot
        existing = get_meal_plan_by_slot(session, user_id, target_date, meal_type)
        if existing:
            # Update the existing plan
            if recipe_id is not None:
                existing.recipe_id = recipe_id
            if servings is not None:
                existing.servings = servings
            session.commit()
            return {
                "id": existing.id,
                "date": str(existing.date),
                "meal_type": existing.meal_type,
                "recipe_id": existing.recipe_id,
                "servings": existing.servings,
                "status": existing.status,
                "action": "updated",
            }

        # Create new plan
        plan = create_meal_plan(
            session,
            user_id=user_id,
            date=target_date,
            meal_type=meal_type,
            recipe_id=recipe_id,
            servings=servings,
            status="planned",
        )
        return {
            "id": plan.id,
            "date": str(plan.date),
            "meal_type": plan.meal_type,
            "recipe_id": plan.recipe_id,
            "servings": plan.servings,
            "status": plan.status,
            "action": "created",
        }
    finally:
        session.close()


def pick_suggestion(suggestions: list[MealSuggestion], choice: int = -1) -> MealSuggestion:
    """Pick a suggestion by index, or randomly if choice == -1 (surprise me).

    Args:
        suggestions: List of meal suggestions
        choice: 1-based index, or -1 for random

    Returns:
        The chosen MealSuggestion

    Raises:
        ValueError if no suggestions or index out of range
    """
    if not suggestions:
        raise ValueError("No suggestions available to pick from.")

    if choice == -1:
        return random.choice(suggestions)

    # 1-based indexing for user friendliness
    idx = choice - 1
    if idx < 0 or idx >= len(suggestions):
        raise ValueError(
            f"Invalid choice {choice}. Pick a number between 1 and {len(suggestions)}."
        )
    return suggestions[idx]


# ─── Plan a day ────────────────────────────────────────────────────────────

def plan_day(
    user_id: int,
    target_date: date,
    meal_slots: Optional[list[str]] = None,
) -> list[dict]:
    """Plan all meal slots for a given day.

    This returns the meal slots to plan and suggestions for each.
    The CLI should call this iteratively, letting the user pick for each slot.

    Args:
        user_id: The user ID
        target_date: Which day
        meal_slots: Override which slots to plan. If None, uses user preferences.

    Returns:
        List of dicts, each with 'meal_type' and 'suggestions'
    """
    if meal_slots is None:
        meal_slots = _get_user_meal_slots(user_id)

    results = []
    for slot in meal_slots:
        _validate_meal_type(slot)
        suggestions = get_suggestions(user_id, target_date, slot)
        results.append({
            "date": str(target_date),
            "meal_type": slot,
            "suggestions": suggestions,
        })

    return results


# ─── Plan a week ───────────────────────────────────────────────────────────

def plan_week(
    user_id: int,
    start_date: Optional[date] = None,
    meal_slots: Optional[list[str]] = None,
) -> list[dict]:
    """Generate suggestions for a full week of meals.

    If start_date is None, starts from tomorrow.
    The CLI iterates over each day/slot, presenting suggestions and letting
    the user pick.

    Args:
        user_id: The user ID
        start_date: Monday of the planning week. Defaults to tomorrow.
        meal_slots: Override which slots to plan.

    Returns:
        List of dicts, each with 'date', 'meal_type', and 'suggestions'
    """
    if start_date is None:
        start_date = date.today() + timedelta(days=1)

    if meal_slots is None:
        meal_slots = _get_user_meal_slots(user_id)

    results = []
    for day_offset in range(7):
        target_date = start_date + timedelta(days=day_offset)
        for slot in meal_slots:
            _validate_meal_type(slot)
            suggestions = get_suggestions(user_id, target_date, slot)
            results.append({
                "date": str(target_date),
                "meal_type": slot,
                "suggestions": suggestions,
            })

    return results


# ─── Show plan ─────────────────────────────────────────────────────────────

def show_plan(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list:
    """Show meal plans for a date range.

    Args:
        user_id: The user ID
        start_date: Start of range (default: today)
        end_date: End of range (default: start_date + 6 days)

    Returns:
        List of MealPlan ORM objects
    """
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=6)

    session = SessionLocal()
    try:
        plans = get_meal_plans(session, user_id, start_date=start_date, end_date=end_date)
        return plans
    finally:
        session.close()


# ─── Clear plan ────────────────────────────────────────────────────────────

def clear_plan(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> int:
    """Delete meal plans in a date range.

    Args:
        user_id: The user ID
        start_date: Start of range (default: today)
        end_date: End of range (default: start_date + 6 days)

    Returns:
        Number of plans deleted
    """
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=6)

    session = SessionLocal()
    try:
        return crud_clear_plans(session, user_id, start_date=start_date, end_date=end_date)
    finally:
        session.close()


# ─── Update status ─────────────────────────────────────────────────────────

def update_status(plan_id: int, status: str) -> dict:
    """Update the status of a meal plan.

    Args:
        plan_id: The meal plan ID
        status: New status (planned, shopped, cooked, skipped)

    Returns:
        Dict with updated plan details
    """
    status = _validate_status(status)

    session = SessionLocal()
    try:
        plan = crud_update_status(session, plan_id, status)
        return {
            "id": plan.id,
            "date": str(plan.date),
            "meal_type": plan.meal_type,
            "recipe_id": plan.recipe_id,
            "servings": plan.servings,
            "status": plan.status,
        }
    finally:
        session.close()