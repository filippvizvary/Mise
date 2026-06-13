"""Meal planning E2E tests — suggestions, plan day/week, show, clear, status."""

import pytest
from datetime import date, timedelta
from unittest.mock import patch
from typer.testing import CliRunner

from mise.cli.main import app
from mise.auth.auth import register as auth_register, login as auth_login, logout as auth_logout, _delete_auth_file
from mise.meal.suggestions import MealSuggestion


class TestMealSuggestions:
    """Test meal suggestion commands."""

    def test_suggest_without_login(self, cli_runner, fresh_db):
        """Suggest command should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["plan", "suggest", "--meal", "lunch"])
        assert result.exit_code != 0

    def test_suggest_with_mock_ai(self, cli_runner, fresh_db, authenticated_user, mock_ai_suggestions):
        """Suggest command should work with mocked AI."""
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", "lunch",
            "--date", (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        ])
        assert result.exit_code == 0
        # Should show at least one suggestion
        assert len(result.output) > 50

    def test_suggest_invalid_meal_type(self, cli_runner, fresh_db, authenticated_user, mock_ai):
        """Suggest with invalid meal type should fail."""
        result = cli_runner.invoke(app, ["plan", "suggest", "--meal", "snacktime"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    @pytest.mark.parametrize("meal_type", ["breakfast", "lunch", "dinner", "brunch", "morning_snack", "afternoon_snack"])
    def test_suggest_all_meal_types(self, cli_runner, fresh_db, authenticated_user, mock_ai_suggestions, meal_type):
        """All valid meal types should be accepted."""
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", meal_type,
            "--date", (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        ])
        assert result.exit_code == 0

    def test_suggest_invalid_date_format(self, cli_runner, fresh_db, authenticated_user, mock_ai):
        """Suggest with invalid date format should fail."""
        result = cli_runner.invoke(app, [
            "plan", "suggest",
            "--meal", "lunch",
            "--date", "not-a-date",
        ])
        assert result.exit_code != 0


class TestPlanCommands:
    """Test individual meal plan commands (breakfast, lunch, dinner, etc.)."""

    def test_plan_lunch_without_login(self, cli_runner, fresh_db):
        """Plan lunch should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["plan", "lunch"], input="1\n")
        assert result.exit_code != 0

    def test_plan_lunch_with_mock_ai(self, cli_runner, fresh_db, authenticated_user, mock_ai_for_planning):
        """Plan lunch should work with mocked AI."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "lunch",
            "--date", tomorrow,
        ], input="1\n")
        assert result.exit_code == 0

    def test_plan_breakfast_with_mock_ai(self, cli_runner, fresh_db, authenticated_user, mock_ai_for_planning):
        """Plan breakfast should work with mocked AI."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "breakfast",
            "--date", tomorrow,
        ], input="1\n")
        assert result.exit_code == 0

    def test_plan_dinner_with_mock_ai(self, cli_runner, fresh_db, authenticated_user, mock_ai_for_planning):
        """Plan dinner should work with mocked AI."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "dinner",
            "--date", tomorrow,
        ], input="1\n")
        assert result.exit_code == 0


class TestPlanShow:
    """Test the plan show command."""

    def test_show_without_login(self, cli_runner, fresh_db):
        """Plan show should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["plan", "show"])
        assert result.exit_code != 0

    def test_show_empty_plan(self, cli_runner, fresh_db, authenticated_user):
        """Show should handle having no meal plans gracefully."""
        result = cli_runner.invoke(app, ["plan", "show"])
        assert result.exit_code == 0
        # Should indicate no plans found or show empty table

    def test_show_with_date_range(self, cli_runner, fresh_db, authenticated_user):
        """Show should accept date range parameters."""
        today = date.today().strftime("%Y-%m-%d")
        next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(app, [
            "plan", "show",
            "--start", today,
            "--end", next_week,
        ])
        assert result.exit_code == 0


class TestPlanClear:
    """Test the plan clear command."""

    def test_clear_without_login(self, cli_runner, fresh_db):
        """Plan clear should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["plan", "clear"], input="y\n")
        assert result.exit_code != 0

    def test_clear_empty_plan(self, cli_runner, fresh_db, authenticated_user):
        """Clearing an empty plan should work."""
        result = cli_runner.invoke(app, ["plan", "clear"], input="y\n")
        assert result.exit_code == 0


class TestPlanStatus:
    """Test the plan status update command."""

    def test_status_without_login(self, cli_runner, fresh_db):
        """Plan status should fail without login."""
        # This command doesn't require login (it takes plan_id as argument)
        # but the plan_id won't exist, so it should fail
        result = cli_runner.invoke(app, ["plan", "status", "999", "cooked"])
        # Should fail because plan doesn't exist
        assert result.exit_code != 0

    def test_status_invalid_status(self, cli_runner, fresh_db, authenticated_user):
        """Setting an invalid status should fail."""
        result = cli_runner.invoke(app, ["plan", "status", "1", "invalid_status"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    @pytest.mark.parametrize("status", ["planned", "shopped", "cooked", "skipped"])
    def test_status_valid_statuses(self, cli_runner, fresh_db, authenticated_user, status):
        """All valid statuses should be accepted by the status command."""
        result = cli_runner.invoke(app, ["plan", "status", "999", status])
        # Will fail because plan 999 doesn't exist, but the status value should be accepted
        # (we're testing that the validation accepts these status values)
        # The error should be about the plan not existing, not invalid status
        if result.exit_code != 0:
            assert "invalid status" not in result.output.lower()


class TestPlanWithoutAuth:
    """Verify all plan commands require authentication."""

    @pytest.mark.parametrize("cmd", [
        ["plan", "breakfast"],
        ["plan", "lunch"],
        ["plan", "dinner"],
        ["plan", "brunch"],
        ["plan", "morning-snack"],
        ["plan", "afternoon-snack"],
        ["plan", "day"],
        ["plan", "week"],
        ["plan", "suggest", "--meal", "lunch"],
        ["plan", "show"],
        ["plan", "clear"],
    ])
    def test_plan_commands_require_auth(self, cli_runner, fresh_db, cmd):
        """All plan commands should require authentication."""
        _delete_auth_file()
        # For commands that need interactive input, provide some default
        input_text = "1\n" if cmd[-1] not in ("show", "clear", "--meal") else None
        if cmd[-1] == "clear":
            input_text = "y\n"
        result = cli_runner.invoke(app, cmd, input=input_text)
        assert result.exit_code != 0, f"Command {' '.join(cmd)} should require auth but got exit_code=0"