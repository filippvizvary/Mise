"""Base classes and models for scrapers."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class DiscountItem(BaseModel):
    """A single discount entry scraped from a store.

    Maps directly to the discounts table in the database.
    """

    store: str
    product: str
    category: Optional[str] = None
    original_price: float
    discount_price: float
    discount_percent: Optional[int] = None
    valid_until: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to a dict suitable for insert_discounts(), dropping None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class BaseScraper(ABC):
    """Abstract base class for all store scrapers.

    Subclass this and implement the ``scrape`` method to add a new store.
    Register the subclass with :class:`ScraperRegistry` so the CLI can find it.
    """

    name: str = "unknown"
    base_url: str = ""

    @abstractmethod
    async def scrape(self) -> list[DiscountItem]:
        """Fetch current discounts from the store.

        Returns a list of :class:`DiscountItem` instances.
        """

    async def run(self) -> list[DiscountItem]:
        """Run the scraper with error handling and logging.

        Wraps :meth:`scrape` so callers don't need to handle
        scraper-specific exceptions.
        """
        from rich.console import Console

        console = Console()
        console.print(f"[bold blue]⏳ Scraping {self.name}…[/bold blue]")
        try:
            items = await self.scrape()
            console.print(f"[green]✓ {self.name}: found {len(items)} discounts[/green]")
            return items
        except Exception as exc:
            console.print(f"[red]✗ {self.name}: {exc}[/red]")
            return []