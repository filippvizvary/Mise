"""Mise configuration – paths and default settings."""

import os

# ── Database ────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("MISE_DB", "data/mise.db")

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