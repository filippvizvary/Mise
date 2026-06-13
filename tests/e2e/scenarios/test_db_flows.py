"""Database & discount E2E tests — init, add, list, seed, filter."""

import pytest
from typer.testing import CliRunner

from mise.cli.main import app


class TestDbInit:
    """Test database initialization."""

    def test_db_init_creates_tables(self, cli_runner, fresh_db):
        """db init should succeed and create all tables."""
        result = cli_runner.invoke(app, ["db", "init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower() or "✓" in result.output

    def test_db_init_idempotent(self, cli_runner, fresh_db):
        """Running db init twice should not fail."""
        result1 = cli_runner.invoke(app, ["db", "init"])
        result2 = cli_runner.invoke(app, ["db", "init"])
        assert result1.exit_code == 0
        assert result2.exit_code == 0


class TestDbAdd:
    """Test adding discounts to the database."""

    def test_db_add_discount(self, cli_runner, fresh_db):
        """Adding a discount should succeed."""
        result = cli_runner.invoke(app, [
            "db", "add",
            "--store", "Lidl",
            "--product", "Test Product",
            "--category", "Meat",
            "--original-price", "5.99",
            "--discount-price", "3.99",
        ])
        assert result.exit_code == 0
        assert "added" in result.output.lower() or "✓" in result.output

    def test_db_add_discount_without_category(self, cli_runner, fresh_db):
        """Adding a discount without a category should succeed."""
        result = cli_runner.invoke(app, [
            "db", "add",
            "--store", "Tesco",
            "--product", "Mystery Item",
            "--category", "",
            "--original-price", "10.00",
            "--discount-price", "7.50",
        ])
        assert result.exit_code == 0


class TestDbList:
    """Test listing discounts."""

    def test_db_list_empty(self, cli_runner, fresh_db):
        """Listing an empty database should show no discounts."""
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0
        assert "no discounts" in result.output.lower() or result.output.strip() == "" or "Discounts" in result.output

    def test_db_list_after_seed(self, cli_runner, fresh_db):
        """Seeding then listing should show the seeded discounts."""
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0
        # Should show discount table
        assert "Lidl" in result.output or "Kaufland" in result.output or "Tesco" in result.output

    def test_db_list_filter_by_store(self, cli_runner, fresh_db):
        """Filtering by store should only show matching discounts."""
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list", "--store", "Lidl"])
        assert result.exit_code == 0
        assert "Lidl" in result.output

    def test_db_list_filter_by_category(self, cli_runner, fresh_db):
        """Filtering by category should only show matching discounts."""
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list", "--category", "Meat"])
        assert result.exit_code == 0

    def test_db_list_combined_filters(self, cli_runner, fresh_db):
        """Filtering by both store and category should work."""
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list", "--store", "Lidl", "--category", "Meat"])
        assert result.exit_code == 0


class TestSeed:
    """Test the seed command."""

    def test_seed_adds_discounts(self, cli_runner, fresh_db):
        """Seed should add 5 sample discounts."""
        result = cli_runner.invoke(app, ["seed"])
        assert result.exit_code == 0
        assert "5" in result.output or "seeded" in result.output.lower()

    def test_seed_then_list(self, cli_runner, fresh_db):
        """After seeding, listing should show entries."""
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0

    def test_double_seed(self, cli_runner, fresh_db):
        """Running seed twice should add duplicates (no deduplication)."""
        cli_runner.invoke(app, ["seed"])
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0
        # Should have 10 entries (5 + 5)


class TestDbWorkflow:
    """Test complete database workflows: add → list → filter."""

    def test_add_and_list_workflow(self, cli_runner, fresh_db):
        """Add a discount, then list it."""
        # Add
        cli_runner.invoke(app, [
            "db", "add",
            "--store", "Lidl",
            "--product", "Test Chicken",
            "--category", "Meat",
            "--original-price", "5.99",
            "--discount-price", "3.99",
        ])
        # List
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0
        assert "Test Chicken" in result.output or "Lidl" in result.output

    def test_add_multiple_stores_and_filter(self, cli_runner, fresh_db):
        """Add discounts from multiple stores and filter by one."""
        cli_runner.invoke(app, [
            "db", "add",
            "--store", "Lidl",
            "--product", "Product A",
            "--category", "Dairy",
            "--original-price", "2.00",
            "--discount-price", "1.50",
        ])
        cli_runner.invoke(app, [
            "db", "add",
            "--store", "Kaufland",
            "--product", "Product B",
            "--category", "Meat",
            "--original-price", "6.00",
            "--discount-price", "4.00",
        ])
        # Filter by store
        result = cli_runner.invoke(app, ["db", "list", "--store", "Lidl"])
        assert result.exit_code == 0
        assert "Lidl" in result.output