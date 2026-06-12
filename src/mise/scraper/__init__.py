"""Mise scraper module – discount scrapers for various stores.

Importing this module automatically registers all built-in scrapers
with the global :data:`scraper_registry`.
"""

from mise.scraper.base import BaseScraper, DiscountItem
from mise.scraper.registry import scraper_registry

# ── Register built-in scrapers ──────────────────────────────────────
from mise.scraper.lidl import LidlScraper       # noqa: E402, F401
from mise.scraper.kaufland import KauflandScraper  # noqa: E402, F401
from mise.scraper.tesco import TescoScraper       # noqa: E402, F401

scraper_registry.register("lidl", LidlScraper)
scraper_registry.register("kaufland", KauflandScraper)
scraper_registry.register("tesco", TescoScraper)

__all__ = [
    "BaseScraper",
    "DiscountItem",
    "scraper_registry",
    "LidlScraper",
    "KauflandScraper",
    "TescoScraper",
]