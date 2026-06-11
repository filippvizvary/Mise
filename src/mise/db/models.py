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


def insert_discounts(discounts: list):
    """Insert a list of discount dicts into the database.

    Each dict should have keys: store, product, category, original_price, discount_price
    Optional keys: discount_percent, valid_until, url
    """
    conn = _get_conn()
    cursor = conn.cursor()
    for d in discounts:
        cursor.execute(
            "INSERT INTO discounts (store, product, category, original_price, discount_price) "
            "VALUES (?, ?, ?, ?, ?)",
            (d["store"], d["product"], d["category"], d["original_price"], d["discount_price"]),
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