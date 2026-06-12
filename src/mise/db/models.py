"""Database management for Mise."""

import sqlite3
from mise.config import DB_PATH


def _get_conn():
    """Open a connection to the database. Creates the data/ folder if needed."""
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return dict-like rows instead of tuples
    return conn


def init_db():
    """Create the discounts table if it doesn't exist."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS discounts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "store TEXT NOT NULL,"
        "product TEXT NOT NULL,"
        "category TEXT,"
        "original_price REAL,"
        "discount_price REAL,"
        "discount_percent INTEGER,"
        "valid_until TEXT,"
        "url TEXT"
        ");"
    )
    conn.commit()
    conn.close()


def _normalize_discount(d):
    """Accept a dict or a DiscountItem and return a normalized dict with all fields."""
    # If it's a Pydantic model (DiscountItem), convert to dict
    if hasattr(d, "model_dump"):
        data = d.model_dump()
    else:
        data = dict(d)

    # Ensure all keys exist (with None defaults for optional fields)
    return {
        "store": data.get("store"),
        "product": data.get("product"),
        "category": data.get("category"),
        "original_price": data.get("original_price"),
        "discount_price": data.get("discount_price"),
        "discount_percent": data.get("discount_percent"),
        "valid_until": data.get("valid_until"),
        "url": data.get("url"),
    }


def insert_discounts(discounts: list):
    """Insert a list of discount dicts or DiscountItems into the database.

    Each item can be a dict with keys: store, product, category, original_price, discount_price
    Optional keys: discount_percent, valid_until, url

    Or a :class:`mise.scraper.base.DiscountItem` instance.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    for d in discounts:
        data = _normalize_discount(d)
        cursor.execute(
            "INSERT INTO discounts (store, product, category, original_price, discount_price, discount_percent, valid_until, url) "
            "VALUES (:store, :product, :category, :original_price, :discount_price, :discount_percent, :valid_until, :url)",
            data,
        )
    conn.commit()
    conn.close()


def get_discounts(store: str = None, category: str = None) -> list:
    """Query discounts with optional filters. Returns a list of sqlite3.Row objects."""
    conn = _get_conn()
    cursor = conn.cursor()
    if store is None and category is None:
        cursor.execute("SELECT * FROM discounts;")
    elif category is None:
        cursor.execute("SELECT * FROM discounts WHERE store = ?;", (store,))
    elif store is None:
        cursor.execute("SELECT * FROM discounts WHERE category = ?;", (category,))
    else:
        cursor.execute("SELECT * FROM discounts WHERE store = ? AND category = ?;", (store, category))

    results = cursor.fetchall()
    conn.close()
    return results