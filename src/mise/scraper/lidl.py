"""Lidl discount scraper."""

from mise.scraper.base import BaseScraper, DiscountItem


class LidlScraper(BaseScraper):
    """Scrape current discounts from Lidl.

    TODO: Implement actual HTTP/Playwright scraping logic.
    The current implementation returns sample data.
    """

    name = "lidl"
    base_url = "https://www.lidl.sk"

    async def scrape(self) -> list[DiscountItem]:
        """Fetch discounts from Lidl's weekly offers page.

        Future implementation should:
        1. Use httpx or Playwright to fetch the offers page
        2. Parse HTML with BeautifulSoup
        3. Extract product name, prices, category, validity
        4. Return a list of DiscountItem instances
        """
        # Placeholder – will be replaced with real scraping logic
        return [
            DiscountItem(
                store="Lidl",
                product="Chicken Breast 500g",
                category="Meat",
                original_price=5.99,
                discount_price=3.99,
                discount_percent=33,
                url=f"{self.base_url}/offers",
            ),
        ]