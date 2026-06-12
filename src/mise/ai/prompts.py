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