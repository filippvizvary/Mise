"""Mise configuration – paths, default settings, and environment variables."""

import os

from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()

# ── Database ────────────────────────────────────────────────────────────
# Default to SQLite for easy local dev; set DATABASE_URL for PostgreSQL
_default_db_url = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mise.db")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    _default_db_url,
)

# ── AI Provider ─────────────────────────────────────────────────────────
DEFAULT_AI_PROVIDER = os.environ.get("MISE_AI_PROVIDER", "ollama")
DEFAULT_AI_MODEL = os.environ.get("MISE_AI_MODEL", "glm-5.1")

# Ollama-specific
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")

# OpenAI-specific
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

# ── Scraper ─────────────────────────────────────────────────────────────
SCRAPER_TIMEOUT = int(os.environ.get("MISE_SCRAPER_TIMEOUT", "30"))  # seconds
SCRAPER_HEADLESS = os.environ.get("MISE_SCRAPER_HEADLESS", "true").lower() == "true"

# ── Auth ────────────────────────────────────────────────────────────────
AUTH_FILE = os.path.join(os.path.expanduser("~"), ".mise", "auth")

# ── Email ──────────────────────────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "mise@example.com")
EMAIL_VERIFICATION_REQUIRED = os.environ.get("EMAIL_VERIFICATION_REQUIRED", "true").lower() == "true"

# ── User defaults ───────────────────────────────────────────────────────
DEFAULT_HOUSEHOLD_SIZE = 1
DEFAULT_UNITS = "metric"
DEFAULT_CURRENCY = "EUR"
DEFAULT_WEEKLY_BUDGET = None  # no budget limit by default
DEFAULT_LANGUAGE = "en"  # English only for now, expandable later
DEFAULT_COOKING_SKILL = "intermediate"

# ── Planning ────────────────────────────────────────────────────────────
DEFAULT_PLANNING_HORIZON_DAYS = 7
MEAL_SLOTS = ["breakfast", "lunch", "dinner"]

# ── Price comparison (discounts only) ──────────────────────────────────
MAX_STORE_VISITS = 3  # don't recommend visiting more than 3 stores
PREFERRED_STORES_ORDER: list[str] = []  # user preference, empty = no preference

# ── Cook Mode ───────────────────────────────────────────────────────────
MEAL_SLOT_BREAKFAST = (6, 9)  # 6am–9am
MEAL_SLOT_LUNCH = (11, 14)  # 11am–2pm
MEAL_SLOT_DINNER = (17, 21)  # 5pm–9pm