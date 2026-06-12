"""Kaufland discount scraper."""

from mise.scraper.base import BaseScraper, DiscountItem


class KauflandScraper(BaseScraper):
    """Scrape current discounts from Kaufland.

    TODO: Implement actual HTTP/Playwright scraping logic.
    The current implementation returns sample data.
    """

    name = "kaufland"
    base_url = "https://www.kaufland.sk"

    async def scrape(self) -> list[DiscountItem]:
        """Fetch discounts from Kaufland's weekly offers page.

        Future implementation should:
        1. Use httpx or Playwright to fetch the offers page
        2. Parse HTML with BeautifulSoup
        3. Extract product name, prices, category, validity
        4. Return a list of DiscountItem instances
        """
        # Placeholder – will be replaced with real scraping logic
        return [
            DiscountItem(
                store="Kaufland",
                product="Pork Shoulder 1kg",
                category="Meat",
                original_price=6.99,
                discount_price=4.49,
                discount_percent=36,
                url=f"{self.base_url}/offers",
            ),
        ]