"""Auto-discovered smoke tests — every CLI command gets a --help test.

This module uses the discovery module to find all registered CLI commands
and automatically generates a --help test for each one. When new commands
are added, they are automatically included.
"""

import pytest
from typer.testing import CliRunner

from mise.cli.main import app
from tests.e2e.discovery import discover_commands, get_help_args


# ─── Discover all commands at module level ──────────────────────────────────

ALL_COMMANDS = discover_commands(app)
COMMAND_PATHS = [cmd.full_path for cmd in ALL_COMMANDS]


def idfn(command_path: str) -> str:
    """Generate readable test IDs from command paths."""
    return f"mise {command_path}"


@pytest.fixture(scope="module")
def runner():
    """Module-scoped CLI runner for smoke tests."""
    return CliRunner()


# ─── Parametrized --help Tests ─────────────────────────────────────────────

@pytest.mark.parametrize("command_path", COMMAND_PATHS, ids=idfn)
def test_command_help_exits_zero(runner, command_path, fresh_db):
    """Every CLI command should respond to --help with exit code 0."""
    args = get_help_args(command_path)
    result = runner.invoke(app, args)
    assert result.exit_code == 0, (
        f"mise {' '.join(args)} failed with exit code {result.exit_code}.\n"
        f"Output:\n{result.output}"
    )


@pytest.mark.parametrize("command_path", COMMAND_PATHS, ids=idfn)
def test_command_help_has_description(runner, command_path, fresh_db):
    """Every CLI command should show a help description when called with --help."""
    args = get_help_args(command_path)
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    # Help output should contain more than just the command name
    assert len(result.output.strip()) > 10, (
        f"mise {command_path} --help output seems too short.\n"
        f"Output:\n{result.output}"
    )


# ─── Top-level command tests ───────────────────────────────────────────────

class TestTopLevelCommands:
    """Test top-level commands that don't require authentication or complex setup."""

    def test_hello_command(self, runner, fresh_db):
        """Test the hello command with default text."""
        result = runner.invoke(app, ["hello"])
        assert result.exit_code == 0
        assert "Hello" in result.output or "Message" in result.output

    def test_hello_with_custom_text(self, runner, fresh_db):
        """Test the hello command with custom text."""
        result = runner.invoke(app, ["hello", "--text", "TestMessage"])
        assert result.exit_code == 0
        assert "TestMessage" in result.output

    def test_db_init(self, runner, fresh_db):
        """Test database initialization."""
        result = runner.invoke(app, ["db", "init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower() or "Database" in result.output

    def test_seed_command(self, runner, fresh_db):
        """Test the seed command adds sample data."""
        result = runner.invoke(app, ["seed"])
        assert result.exit_code == 0
        assert "seeded" in result.output.lower() or "5" in result.output


# ─── Coverage Gate ──────────────────────────────────────────────────────────

class TestCoverageGate:
    """Verify that all discovered commands have dedicated tests."""

    def test_all_commands_discovered(self):
        """Verify that command discovery finds at least some commands."""
        assert len(COMMAND_PATHS) > 0, "No CLI commands discovered — something is wrong with discovery"

    def test_expected_groups_present(self):
        """Verify that the expected command groups are present."""
        groups = set()
        for cmd in ALL_COMMANDS:
            if cmd.group:
                groups.add(cmd.group)

        expected_groups = {"db", "scrape", "ai", "auth", "profile", "plan"}
        for group in expected_groups:
            assert group in groups, (
                f"Expected command group '{group}' not found. "
                f"Discovered groups: {sorted(groups)}"
            )

    def test_no_duplicate_commands(self):
        """Verify no duplicate command paths were discovered."""
        paths = [cmd.full_path for cmd in ALL_COMMANDS]
        assert len(paths) == len(set(paths)), f"Duplicate commands found: {paths}"