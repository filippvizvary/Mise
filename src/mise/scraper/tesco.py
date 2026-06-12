"""Tesco discount scraper."""

from mise.scraper.base import BaseScraper, DiscountItem


class TescoScraper(BaseScraper):
    """Scrape current discounts from Tesco.

    TODO: Implement actual HTTP/Playwright scraping logic.
    The current implementation returns sample data.
    """

    name = "tesco"
    base_url = "https://www.tesco.sk"

    async def scrape(self) -> list[DiscountItem]:
        """Fetch discounts from Tesco's weekly offers page.

        Future implementation should:
        1. Use httpx or Playwright to fetch the offers page
        2. Parse HTML with BeautifulSoup
        3. Extract product name, prices, category, validity
        4. Return a list of DiscountItem instances
        """
        # Placeholder – will be replaced with real scraping logic
        return [
            DiscountItem(
                store="Tesco",
                product="Salmon Fillet 200g",
                category="Fish",
                original_price=7.99,
                discount_price=5.49,
                discount_percent=31,
                url=f"{self.base_url}/offers",
            ),
        ]