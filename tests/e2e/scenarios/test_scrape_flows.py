"""Scraper E2E tests — run, list, save discounts (all mocked)."""

import pytest
from typer.testing import CliRunner

from mise.cli.main import app


class TestScrapeList:
    """Test listing available scrapers."""

    def test_scrape_list(self, cli_runner, fresh_db, mock_scraper):
        """Listing scrapers should show available stores."""
        result = cli_runner.invoke(app, ["scrape", "list"])
        assert result.exit_code == 0
        assert "lidl" in result.output.lower() or "kaufland" in result.output.lower() or "tesco" in result.output.lower()


class TestScrapeRun:
    """Test running scrapers (mocked)."""

    def test_scrape_run_specific_store(self, cli_runner, fresh_db, mock_scraper):
        """Running a specific store scraper should show results."""
        result = cli_runner.invoke(app, ["scrape", "run", "lidl"])
        assert result.exit_code == 0

    def test_scrape_run_all_stores(self, cli_runner, fresh_db, mock_scraper):
        """Running all scrapers should show results."""
        result = cli_runner.invoke(app, ["scrape", "run"])
        assert result.exit_code == 0

    def test_scrape_run_and_save(self, cli_runner, fresh_db, mock_scraper):
        """Running scraper with --save should persist discounts."""
        result = cli_runner.invoke(app, ["scrape", "run", "--save"])
        assert result.exit_code == 0

    def test_scrape_run_empty(self, cli_runner, fresh_db, mock_scraper_empty):
        """Running scraper that returns no discounts should handle gracefully."""
        result = cli_runner.invoke(app, ["scrape", "run"])
        assert result.exit_code == 0
        assert "no discounts" in result.output.lower() or result.output.strip() == ""

    def test_scrape_specific_store_empty(self, cli_runner, fresh_db, mock_scraper_empty):
        """Running a specific empty scraper should handle gracefully."""
        result = cli_runner.invoke(app, ["scrape", "run", "lidl"])
        assert result.exit_code == 0

    def test_scrape_run_and_save_then_list(self, cli_runner, fresh_db, mock_scraper):
        """Run scraper, save results, then list them."""
        # Scrape and save
        cli_runner.invoke(app, ["scrape", "run", "--save"])
        # List
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0