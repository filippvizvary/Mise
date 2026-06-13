"""AI-powered meal suggestion engine.

Generates meal suggestions by:
1. Gathering user context (profile, preferences, inventory, discounts, existing plans)
2. Building a structured prompt for the AI
3. Parsing the AI response into typed MealSuggestion objects
"""

import json
import re
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from mise.ai.prompts import MEAL_SUGGEST_SYSTEM, MEAL_SUGGEST_PROMPT


# ─── Meal types ──────────────────────────────────────────────────────────

class MealType(str, Enum):
    """Canonical meal type values."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    BRUNCH = "brunch"
    MORNING_SNACK = "morning_snack"
    AFTERNOON_SNACK = "afternoon_snack"


# ─── Suggestion model ────────────────────────────────────────────────────

class MealSuggestion(BaseModel):
    """A single meal suggestion returned by the AI."""
    title: str = Field(description="Recipe or meal title")
    recipe_id: Optional[str] = Field(default=None, description="Linked recipe slug if known")
    reason: str = Field(description="Why this meal is suggested")
    ingredient_overlap: list[str] = Field(default_factory=list, description="Ingredients already in inventory")
    discount_match: Optional[str] = Field(default=None, description="Discount that influenced this suggestion")
    cuisine: Optional[str] = Field(default=None, description="Cuisine type")
    prep_time_min: Optional[int] = Field(default=None, description="Estimated prep time")
    difficulty: Optional[str] = Field(default=None, description="easy, medium, or hard")


# ─── Context builder ──────────────────────────────────────────────────────

def build_meal_context(user_id: int, target_date: date, meal_type: str) -> dict:
    """Gather all relevant context for generating meal suggestions.

    Returns a dict with:
    - user_profile: household size, cooking skill, budget, max cook time
    - preferences: allergies, dislikes, liked cuisines, preferred stores
    - existing_plans: meals already planned for the week
    - inventory: items currently in pantry
    - discounts: current discounts at preferred stores
    - feedback: recent feedback history (ratings, would_repeat)
    - shopping_list: items already on the shopping list
    """
    from mise.db.database import SessionLocal
    from mise.db.crud import (
        get_meal_plans,
        get_user_inventory,
        get_discounts_for_stores,
        get_user_feedback,
        get_user_shopping_items,
    )
    from mise.db.models import User
    from mise.user.preferences import list_preferences

    session = SessionLocal()
    try:
        # Load user and profile
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError(f"User {user_id} not found")

        profile = user.profile

        # Profile info
        profile_dict = {}
        if profile:
            profile_dict = {
                "household_size": profile.household_size,
                "cooking_skill": profile.cooking_skill,
                "weekly_budget": profile.weekly_budget,
                "max_cook_time_min": profile.max_cook_time_min,
                "preferred_units": profile.preferred_units,
            }

        # Preferences
        prefs = list_preferences(user_id)
        allergies = [p.pref_value for p in prefs if p.pref_type == "allergy"]
        dislikes = [p.pref_value for p in prefs if p.pref_type == "dislike"]
        liked_cuisines = [p.pref_value for p in prefs if p.pref_type == "liked_cuisine"]
        preferred_stores = [p.pref_value for p in prefs if p.pref_type == "preferred_store"]
        meal_slots = [p.pref_value for p in prefs if p.pref_type == "meal_slot"]

        # Existing plans for the week containing target_date
        # ISO week: Monday = start
        weekday = target_date.weekday()
        week_start = target_date - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)

        existing = get_meal_plans(session, user_id, start_date=week_start, end_date=week_end)
        existing_plans = [
            {
                "date": str(p.date),
                "meal_type": p.meal_type,
                "recipe_id": p.recipe_id,
                "status": p.status,
            }
            for p in existing
        ]

        # Inventory
        inventory_items = get_user_inventory(session, user_id)
        inventory_list = [
            {
                "name": item.name,
                "category": item.category,
                "quantity": item.quantity,
                "unit": item.unit,
                "due_date": str(item.due_date) if item.due_date else None,
            }
            for item in inventory_items
        ]

        # Discounts at preferred stores
        discount_list = []
        if preferred_stores:
            discounts = get_discounts_for_stores(session, preferred_stores)
            discount_list = [
                {
                    "store": d.store,
                    "product": d.product,
                    "category": d.category,
                    "original_price": d.original_price,
                    "discount_price": d.discount_price,
                    "discount_percent": d.discount_percent,
                    "valid_until": d.valid_until,
                }
                for d in discounts
            ]

        # Feedback history — recent ratings and would_repeat info
        feedback_items = get_user_feedback(session, user_id)
        feedback_list = [
            {
                "recipe_id": f.recipe_id,
                "rating": f.rating,
                "would_repeat": f.would_repeat,
                "notes": f.notes,
            }
            for f in feedback_items
            if f.recipe_id is not None
        ]

        # Shopping list items (unchecked) — already planned to buy
        shopping_items = get_user_shopping_items(session, user_id)
        shopping_list = [
            {
                "name": item.ingredient_name,
                "quantity": item.quantity_needed,
                "unit": item.unit_needed,
                "has_discount": item.has_discount,
                "best_store": item.best_store,
            }
            for item in shopping_items
        ]

        return {
            "user_profile": profile_dict,
            "allergies": allergies,
            "dislikes": dislikes,
            "liked_cuisines": liked_cuisines,
            "preferred_stores": preferred_stores,
            "meal_slots": meal_slots,
            "existing_plans": existing_plans,
            "inventory": inventory_list,
            "discounts": discount_list,
            "feedback": feedback_list,
            "shopping_list": shopping_list,
            "target_date": str(target_date),
            "meal_type": meal_type,
        }
    finally:
        session.close()


# ─── AI suggestion generator ──────────────────────────────────────────────

def generate_suggestions(context: dict, meal_type: str, n: int = 5) -> list[MealSuggestion]:
    """Call the AI provider to generate meal suggestions.

    Args:
        context: Output from build_meal_context()
        meal_type: The meal slot to suggest for
        n: Number of suggestions to generate (3-5 recommended)

    Returns:
        List of MealSuggestion objects parsed from AI response.
    """
    from mise.ai import ai_registry

    # Build the prompt
    prompt = MEAL_SUGGEST_PROMPT.format(
        meal_type=meal_type,
        target_date=context.get("target_date", "today"),
        user_profile=json.dumps(context.get("user_profile", {}), ensure_ascii=False),
        allergies=", ".join(context.get("allergies", [])) or "None",
        dislikes=", ".join(context.get("dislikes", [])) or "None",
        liked_cuisines=", ".join(context.get("liked_cuisines", [])) or "Any",
        preferred_stores=", ".join(context.get("preferred_stores", [])) or "Any",
        existing_plans=json.dumps(context.get("existing_plans", []), ensure_ascii=False) or "None",
        inventory=json.dumps(context.get("inventory", []), ensure_ascii=False) or "Empty",
        discounts=json.dumps(context.get("discounts", []), ensure_ascii=False) or "None",
        feedback=json.dumps(context.get("feedback", []), ensure_ascii=False) or "None",
        shopping_list=json.dumps(context.get("shopping_list", []), ensure_ascii=False) or "Empty",
        n=n,
    )

    provider = ai_registry.get()
    response = provider.generate(prompt, system=MEAL_SUGGEST_SYSTEM)

    # Parse the AI response as JSON
    suggestions = _parse_suggestions(response.content)
    return suggestions


def _parse_suggestions(raw: str) -> list[MealSuggestion]:
    """Parse AI response string into MealSuggestion objects.

    The AI is asked to return a JSON array. We handle common
    formatting issues (markdown fences, trailing text).
    """
    # Strip markdown code fences if present
    text = raw.strip()
    # Match ```json, ```JSON, ``` with optional whitespace
    fence_match = re.match(r"^```(?:\w*)\s*\n?", text)
    if fence_match:
        text = text[fence_match.end():]
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON array in the text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                # Return a single suggestion with the raw text as fallback
                return [MealSuggestion(title="AI Suggestion", reason="Could not parse AI response.")]
        else:
            return [MealSuggestion(title="AI Suggestion", reason="Could not parse AI response.")]

    suggestions = []
    for item in data:
        if isinstance(item, dict):
            try:
                suggestions.append(MealSuggestion(**{
                    k: v for k, v in item.items()
                    if k in MealSuggestion.model_fields
                }))
            except Exception:
                # Skip malformed entries
                continue

    return suggestions


def get_suggestions(user_id: int, target_date: date, meal_type: str, n: int = 5) -> list[MealSuggestion]:
    """High-level function: gather context and generate suggestions.

    Args:
        user_id: The user to generate suggestions for
        target_date: Which day
        meal_type: Which meal slot
        n: Number of suggestions (3-5)

    Returns:
        List of MealSuggestion objects
    """
    context = build_meal_context(user_id, target_date, meal_type)
    return generate_suggestions(context, meal_type, n)