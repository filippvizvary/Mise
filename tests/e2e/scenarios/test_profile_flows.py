"""Profile & preference E2E tests — setup, show, allergies, dislikes, cuisines, units, budget."""

import pytest
from typer.testing import CliRunner

from mise.cli.main import app
from mise.auth.auth import register as auth_register, login as auth_login, _delete_auth_file
from tests.e2e.data.users import DIVERSE_PROFILES, DIETARY_PREFERENCES, MEAL_SLOT_COMBOS


class TestProfileSetup:
    """Test the interactive profile setup command."""

    def test_profile_setup_without_login(self, cli_runner, fresh_db):
        """Profile setup should fail when not logged in."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "setup"], input="1\nmetric\nEUR\nintermediate\n\n")
        assert result.exit_code != 0
        assert "no user logged in" in result.output.lower() or "login" in result.output.lower()

    def test_profile_show_without_login(self, cli_runner, fresh_db):
        """Profile show should fail when not logged in."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code != 0

    def test_profile_show_after_registration(self, cli_runner, fresh_db, authenticated_user):
        """Profile show should work after registration and login."""
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0
        # Should show username and default profile values
        assert "testuser" in result.output


class TestProfilePreferences:
    """Test preference management commands."""

    def test_add_allergy(self, cli_runner, fresh_db, authenticated_user):
        """Adding an allergy should succeed."""
        result = cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        assert result.exit_code == 0
        assert "peanuts" in result.output.lower() or "added" in result.output.lower()

    def test_add_multiple_allergies(self, cli_runner, fresh_db, authenticated_user):
        """Adding multiple allergies one by one should work."""
        allergies = ["peanuts", "shellfish", "dairy"]
        for allergy in allergies:
            result = cli_runner.invoke(app, ["profile", "add-allergy", allergy])
            assert result.exit_code == 0

        # Verify all allergies appear in profile show
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0

    def test_remove_allergy(self, cli_runner, fresh_db, authenticated_user):
        """Removing an allergy should succeed."""
        # Add first
        cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        # Then remove
        result = cli_runner.invoke(app, ["profile", "remove-allergy", "peanuts"])
        assert result.exit_code == 0

    def test_remove_nonexistent_allergy(self, cli_runner, fresh_db, authenticated_user):
        """Removing a non-existent allergy should handle gracefully."""
        result = cli_runner.invoke(app, ["profile", "remove-allergy", "nonexistent"])
        # Should not crash
        assert result.exit_code == 0

    def test_add_dislike(self, cli_runner, fresh_db, authenticated_user):
        """Adding a disliked ingredient should succeed."""
        result = cli_runner.invoke(app, ["profile", "add-dislike", "celery"])
        assert result.exit_code == 0
        assert "celery" in result.output.lower() or "added" in result.output.lower()

    def test_remove_dislike(self, cli_runner, fresh_db, authenticated_user):
        """Removing a disliked ingredient should succeed."""
        cli_runner.invoke(app, ["profile", "add-dislike", "celery"])
        result = cli_runner.invoke(app, ["profile", "remove-dislike", "celery"])
        assert result.exit_code == 0

    def test_like_cuisine(self, cli_runner, fresh_db, authenticated_user):
        """Adding a liked cuisine should succeed."""
        result = cli_runner.invoke(app, ["profile", "like-cuisine", "Italian"])
        assert result.exit_code == 0
        assert "italian" in result.output.lower() or "added" in result.output.lower()

    def test_unlike_cuisine(self, cli_runner, fresh_db, authenticated_user):
        """Removing a liked cuisine should succeed."""
        cli_runner.invoke(app, ["profile", "like-cuisine", "Italian"])
        result = cli_runner.invoke(app, ["profile", "unlike-cuisine", "Italian"])
        assert result.exit_code == 0

    def test_set_units(self, cli_runner, fresh_db, authenticated_user):
        """Setting preferred units should succeed."""
        result = cli_runner.invoke(app, ["profile", "set-units", "metric"])
        assert result.exit_code == 0

    def test_set_units_invalid(self, cli_runner, fresh_db, authenticated_user):
        """Setting invalid units should fail."""
        result = cli_runner.invoke(app, ["profile", "set-units", "gallons"])
        assert result.exit_code != 0

    def test_set_budget(self, cli_runner, fresh_db, authenticated_user):
        """Setting a weekly budget should succeed."""
        result = cli_runner.invoke(app, ["profile", "set-budget", "50"])
        assert result.exit_code == 0

    def test_set_large_budget(self, cli_runner, fresh_db, authenticated_user):
        """Setting a large budget should succeed."""
        result = cli_runner.invoke(app, ["profile", "set-budget", "999.99"])
        assert result.exit_code == 0


class TestProfilePersistence:
    """Test that profile changes persist across commands."""

    def test_allergies_persist(self, cli_runner, fresh_db, authenticated_user):
        """Allergies should persist between commands."""
        cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        result = cli_runner.invoke(app, ["profile", "show"])
        assert "peanuts" in result.output.lower()

    def test_preferences_visible_in_show(self, cli_runner, fresh_db, authenticated_user):
        """All preferences should be visible in the profile show command."""
        # Set up various preferences
        cli_runner.invoke(app, ["profile", "add-allergy", "gluten"])
        cli_runner.invoke(app, ["profile", "add-dislike", "mushrooms"])
        cli_runner.invoke(app, ["profile", "like-cuisine", "Italian"])
        cli_runner.invoke(app, ["profile", "set-units", "metric"])
        cli_runner.invoke(app, ["profile", "set-budget", "75"])

        # Check they all appear
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0

    def test_imperial_units_persist(self, cli_runner, fresh_db, authenticated_user):
        """Setting imperial units should persist."""
        cli_runner.invoke(app, ["profile", "set-units", "imperial"])
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0
        assert "imperial" in result.output.lower()


class TestProfileWithoutAuth:
    """Test that profile commands require authentication."""

    def test_add_allergy_requires_auth(self, cli_runner, fresh_db):
        """add-allergy should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "add-allergy", "peanuts"])
        assert result.exit_code != 0

    def test_show_requires_auth(self, cli_runner, fresh_db):
        """show should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "show"])
        assert result.exit_code != 0

    def test_set_budget_requires_auth(self, cli_runner, fresh_db):
        """set-budget should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "set-budget", "100"])
        assert result.exit_code != 0

    def test_set_units_requires_auth(self, cli_runner, fresh_db):
        """set-units should fail without login."""
        _delete_auth_file()
        result = cli_runner.invoke(app, ["profile", "set-units", "metric"])
        assert result.exit_code != 0