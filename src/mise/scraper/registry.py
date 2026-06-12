"""Scraper registry – discover and run scrapers by name."""

from __future__ import annotations

from typing import Type

from mise.scraper.base import BaseScraper, DiscountItem


class ScraperRegistry:
    """Central registry for all store scrapers.

    Usage::

        from mise.scraper.registry import scraper_registry

        # Register a scraper
        scraper_registry.register("lidl", LidlScraper)

        # Get a scraper instance
        scraper = scraper_registry.get("lidl")
        items = await scraper.run()

        # Run all registered scrapers
        all_items = await scraper_registry.run_all()
    """

    def __init__(self) -> None:
        self._scrapers: dict[str, Type[BaseScraper]] = {}

    def register(self, name: str, scraper_cls: Type[BaseScraper]) -> None:
        """Register a scraper class under the given name."""
        self._scrapers[name.lower()] = scraper_cls

    def get(self, name: str) -> BaseScraper:
        """Return an instance of the scraper registered under *name*.

        Raises KeyError if the name is not registered.
        """
        try:
            cls = self._scrapers[name.lower()]
        except KeyError:
            available = ", ".join(self.list_available()) or "(none)"
            raise KeyError(
                f"No scraper registered as '{name}'. Available: {available}"
            ) from None
        return cls()

    def list_available(self) -> list[str]:
        """Return sorted list of registered scraper names."""
        return sorted(self._scrapers.keys())

    async def run_all(self) -> list[DiscountItem]:
        """Run every registered scraper and aggregate the results."""
        all_items: list[DiscountItem] = []
        for name in self.list_available():
            scraper = self.get(name)
            items = await scraper.run()
            all_items.extend(items)
        return all_items

    async def run_one(self, name: str) -> list[DiscountItem]:
        """Run a single scraper by name."""
        scraper = self.get(name)
        return await scraper.run()


# Module-level singleton
scraper_registry = ScraperRegistry()