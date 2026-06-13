"""Full journey E2E tests — complete user lifecycles from signup to meal planning."""

import pytest
from datetime import date, timedelta
from typer.testing import CliRunner

from mise.cli.main import app
from mise.auth.auth import _delete_auth_file


class TestNewUserJourney:
    """Test a complete new user journey: signup → setup → plan → view."""

    def test_complete_new_user_flow(self, cli_runner, fresh_db, mock_ai_for_planning):
        """Full journey: register → login → profile setup → add preferences → plan meals → view plan."""
        # 1. Register a new user
        result = cli_runner.invoke(app, [
            "auth", "register",
            "--username", "journeyuser",
            "--email", "journey@test.com",
            "--password", "Journey123!",
        ])
        assert result.exit_code == 0

        # 2. Login
        result = cli_runner.invoke(app, [
            "auth", "login",
            "--username", "journeyuser",
            "--password", "Journey123!",
        ])
        assert result.exit_code == 0

        # 3. Verify whoami
        result = cli_runner.invoke(app, ["auth", "whoami"])
        assert result.exit_code == 0
        assert "journeyuser" in result.output

        # 4. Set profile preferences
        result = cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        assert result.exit_code == 0

        result = cli_runner.invoke(app, ["profile", "like-cuisine", "Italian"])
        assert result.exit_code == 0

        result = cli_runner.invoke(app, ["profile", "set-budget", "75"])
        assert result.exit_code == 0

        result = cli_runner.invoke(app, ["profile", "set-units", "metric"])
        assert result.exit_code == 0

        # 5. View profile
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0
        assert "journeyuser" in result.output

        # 6. Add discounts (simulating scraped data)
        result = cli_runner.invoke(app, ["seed"])
        assert result.exit_code == 0

        # 7. View discounts
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0

        # 8. Get meal suggestions
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", "lunch",
            "--date", tomorrow,
        ])
        assert result.exit_code == 0

        # 9. View meal plan (should be empty since we only got suggestions)
        result = cli_runner.invoke(app, ["plan", "show"])
        assert result.exit_code == 0

        # 10. Logout
        result = cli_runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0


class TestReturningUserJourney:
    """Test a returning user: login → check plan → update preferences → plan again."""

    def test_returning_user_flow(self, cli_runner, fresh_db, authenticated_user, mock_ai_for_planning):
        """Returning user: login → view profile → update preferences → view plan."""
        # User is already authenticated from fixture

        # 1. View profile
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0

        # 2. Add more preferences
        result = cli_runner.invoke(app, ["profile", "add-dislike", "celery"])
        assert result.exit_code == 0

        result = cli_runner.invoke(app, ["profile", "add-allergy", "shellfish"])
        assert result.exit_code == 0

        # 3. Set budget
        result = cli_runner.invoke(app, ["profile", "set-budget", "100"])
        assert result.exit_code == 0

        # 4. Seed discounts
        result = cli_runner.invoke(app, ["seed"])
        assert result.exit_code == 0

        # 5. View discounts
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0

        # 6. Get suggestions
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", "dinner",
            "--date", tomorrow,
        ])
        assert result.exit_code == 0

        # 7. View empty plan
        result = cli_runner.invoke(app, ["plan", "show"])
        assert result.exit_code == 0


class TestDiscountsToPlanningJourney:
    """Test the flow: scrape discounts → view → plan meals based on them."""

    def test_scrape_to_plan_flow(self, cli_runner, fresh_db, authenticated_user, mock_scraper, mock_ai_for_planning):
        """Scrape → save → view → suggest meals."""
        # 1. Run scraper (mocked)
        result = cli_runner.invoke(app, ["scrape", "run"])
        assert result.exit_code == 0

        # 2. Save scraped data
        result = cli_runner.invoke(app, ["scrape", "run", "--save"])
        assert result.exit_code == 0

        # 3. List discounts from DB
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0

        # 4. Get AI summary (mocked)
        result = cli_runner.invoke(app, ["ai", "summarize"])
        # May or may not have data depending on mock setup

        # 5. Get meal suggestions
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", "lunch",
            "--date", tomorrow,
        ])
        assert result.exit_code == 0


class TestMultiUserJourney:
    """Test two users living side by side."""

    def test_two_users_separate_journeys(self, cli_runner, fresh_db, mock_ai_for_planning):
        """Two users register, set up profiles, and plan independently."""
        # === User A's Journey ===
        cli_runner.invoke(app, ["auth", "register", "--username", "user_a", "--email", "a@test.com", "--password", "PassA123!"])
        cli_runner.invoke(app, ["auth", "login", "--username", "user_a", "--password", "PassA123!"])

        # User A sets up as vegetarian
        cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        cli_runner.invoke(app, ["profile", "like-cuisine", "Italian"])
        cli_runner.invoke(app, ["profile", "set-budget", "50"])

        # User A views profile
        result_a = cli_runner.invoke(app, ["profile", "show"])
        assert result_a.exit_code == 0
        assert "user_a" in result_a.output

        # === User B's Journey ===
        cli_runner.invoke(app, ["auth", "logout"])
        cli_runner.invoke(app, ["auth", "register", "--username", "user_b", "--email", "b@test.com", "--password", "PassB456!"])
        cli_runner.invoke(app, ["auth", "login", "--username", "user_b", "--password", "PassB456!"])

        # User B sets up differently
        cli_runner.invoke(app, ["profile", "add-dislike", "mushrooms"])
        cli_runner.invoke(app, ["profile", "like-cuisine", "Mexican"])
        cli_runner.invoke(app, ["profile", "set-budget", "200"])

        # User B views profile (should show different data)
        result_b = cli_runner.invoke(app, ["profile", "show"])
        assert result_b.exit_code == 0
        assert "user_b" in result_b.output

        # Both users can use shared discount data
        cli_runner.invoke(app, ["seed"])
        result = cli_runner.invoke(app, ["db", "list"])
        assert result.exit_code == 0