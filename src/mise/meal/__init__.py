"""Mise meal planning module.

Provides AI-assisted meal scheduling that considers:
- User profile & preferences (allergies, dislikes, liked cuisines)
- Existing weekly plans (avoids repetition)
- Current inventory (reduces waste)
- Current discounts at preferred stores (efficiency)
- Seasonal availability
"""

from mise.meal.planner import (
    plan_day,
    plan_meal,
    plan_week,
    show_plan,
    clear_plan,
    update_status,
)
from mise.meal.suggestions import get_suggestions

__all__ = [
    "plan_meal",
    "plan_day",
    "plan_week",
    "show_plan",
    "clear_plan",
    "update_status",
    "get_suggestions",
]