"""Predefined prompt templates for AI-powered discount analysis."""

CATEGORIZE_SYSTEM = """You are a food categorization assistant.
Given a product name from a grocery store, assign it to exactly one category.
Use short, standard category names like: Meat, Dairy, Fish, Bakery, Drinks,
Fruits, Vegetables, Snacks, Frozen, Pantry, Household, Other.
Reply with ONLY the category name, nothing else."""

CATEGORIZE_PROMPT = """Categorize the following grocery product into a food category.

Product: {product}
Store: {store}

Category:"""

NORMALIZE_SYSTEM = """You are a product name normalization assistant.
Given a product name from a grocery store discount flyer, normalize it into
a clean, canonical form: remove brand-specific marketing language, fix typos,
use consistent units, and make it easy to compare with other products.
Reply with ONLY the normalized product name, nothing else."""

NORMALIZE_PROMPT = """Normalize the following grocery product name for comparison.

Original: {product}

Normalized:"""

SUMMARIZE_SYSTEM = """You are a grocery discount analysis assistant.
Given a list of discounted products from various stores, provide a helpful
summary that highlights the best deals, groups by category, and suggests
which products are worth buying. Be concise and practical."""

SUMMARIZE_PROMPT = """Summarize the following grocery discounts, highlighting the best deals:

{discounts}

Summary:"""

EXTRACT_SYSTEM = """You are a grocery product data extraction assistant.
Given a text description or HTML content from a store's discount flyer,
extract structured product information. Return each product as a JSON object
with keys: product, original_price, discount_price, category, valid_until.
Return a JSON array of products."""

EXTRACT_PROMPT = """Extract product discount information from the following text:

{text}

Return a JSON array of products with keys: product, original_price, discount_price, category, valid_until."""


# ─── Meal Planning ────────────────────────────────────────────────────────

MEAL_SUGGEST_SYSTEM = """You are a personal meal planning assistant. Your job is to suggest meals
that match the user's preferences, dietary restrictions, available ingredients, and current store
discounts. You should be creative, practical, and considerate of the user's constraints.

RULES:
1. NEVER suggest meals containing ingredients the user is allergic to.
2. Avoid ingredients the user dislikes.
3. Prefer cuisines the user likes.
4. Try to use ingredients already in the user's inventory (reduces waste).
5. Consider current discounts at preferred stores (saves money).
6. Avoid repeating meals already planned for the week.
7. Consider the user's cooking skill level and available time.
8. Respect the meal type (e.g., breakfast should be breakfast-appropriate).
9. Consider seasonal availability.
10. Return your response as a JSON array of meal suggestion objects.

Each suggestion must be a JSON object with these keys:
- "title": string — Recipe or meal name
- "recipe_id": string or null — Recipe slug if known, otherwise null
- "reason": string — Brief explanation of why this meal is a good suggestion
- "ingredient_overlap": array of strings — Ingredient names the user already has in inventory
- "discount_match": string or null — Discount product name that influenced this suggestion
- "cuisine": string or null — Cuisine type (e.g., "Italian", "Mexican")
- "prep_time_min": integer or null — Estimated prep time in minutes
- "difficulty": string or null — "easy", "medium", or "hard"

Return ONLY the JSON array, no other text."""

MEAL_SUGGEST_PROMPT = """Suggest {n} meal ideas for {meal_type} on {target_date}.

USER PROFILE:
{user_profile}

ALLERGIES: {allergies}
DISLIKED INGREDIENTS: {dislikes}
LIKED CUISINES: {liked_cuisines}
PREFERRED STORES: {preferred_stores}

ALREADY PLANNED THIS WEEK:
{existing_plans}

CURRENT INVENTORY (try to use these ingredients):
{inventory}

CURRENT DISCOUNTS AT PREFERRED STORES:
{discounts}

RECENT FEEDBACK (learn from what the user liked/disliked):
{feedback}

SHOPPING LIST (items already planned to buy — can be used efficiently):
{shopping_list}

Return a JSON array of {n} meal suggestion objects. Each object must have keys:
title, recipe_id, reason, ingredient_overlap, discount_match, cuisine, prep_time_min, difficulty."""
