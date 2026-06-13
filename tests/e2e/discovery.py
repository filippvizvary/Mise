"""CLI command discovery — automatically finds all Typer commands for testing.

This module introspects the Mise Typer app at runtime to discover all
registered commands and sub-groups. It's used by:
- Auto-smoke tests (every command gets a --help test)
- Coverage gate (warns about commands without dedicated tests)
- AI testing workflow (knows what to test)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import typer
from typer.testing import CliRunner


@dataclass
class CommandInfo:
    """Information about a discovered CLI command."""

    name: str                    # Command name (e.g. "init", "add", "list")
    full_path: str               # Full path (e.g. "db init", "auth login")
    group: Optional[str]         # Parent group name (e.g. "db", "auth") or None for top-level
    help_text: str               # Help text from docstring
    is_app: bool = False         # True if this is a sub-app/group, not a leaf command


@dataclass
class AppDiscovery:
    """Discovered structure of a Typer app."""

    commands: list[CommandInfo] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)


def discover_commands(app: typer.Typer, prefix: str = "") -> list[CommandInfo]:
    """Recursively discover all commands registered in a Typer app.

    Args:
        app: The Typer app to inspect.
        prefix: Current command path prefix (e.g. "db", "auth").

    Returns:
        List of CommandInfo objects for all leaf commands.
    """
    commands: list[CommandInfo] = []

    # Typer stores registered commands in app.registered_commands
    # and sub-apps in app.registered_groups
    for cmd in app.registered_commands:
        cmd_name = cmd.name or cmd.callback.__name__.replace("_", "-") if cmd.callback else "unknown"
        help_text = ""
        if cmd.callback:
            help_text = (cmd.callback.__doc__ or "").strip().split("\n")[0]
        elif cmd.help:
            help_text = cmd.help or ""

        full_path = f"{prefix} {cmd_name}".strip() if prefix else cmd_name

        commands.append(CommandInfo(
            name=cmd_name,
            full_path=full_path,
            group=prefix or None,
            help_text=help_text,
        ))

    # Typer stores sub-apps (groups) in registered_groups
    for group in app.registered_groups:
        group_name = group.name
        sub_app = group.typer_instance

        if sub_app is not None:
            # Record the group itself
            group_path = f"{prefix} {group_name}".strip() if prefix else group_name

            # Recurse into sub-app
            sub_commands = discover_commands(sub_app, prefix=group_path)
            commands.extend(sub_commands)

    return commands


def get_all_command_paths(app: typer.Typer) -> list[str]:
    """Get all command paths as strings (e.g. ['hello', 'seed', 'db init', ...]).

    Useful for parametrized tests.
    """
    return [cmd.full_path for cmd in discover_commands(app)]


def get_help_args(command_path: str) -> list[str]:
    """Convert a command path to CLI args for --help.

    Example: "db init" -> ["db", "init", "--help"]
    Example: "hello" -> ["hello", "--help"]
    """
    parts = command_path.split()
    return parts + ["--help"]


def discover_groups(app: typer.Typer) -> list[str]:
    """Discover all sub-app/group names."""
    groups = []
    for group in app.registered_groups:
        groups.append(group.name)
    return groups


def print_discovery(app: typer.Typer) -> None:
    """Print a summary of all discovered commands (useful for debugging)."""
    commands = discover_commands(app)
    groups = discover_groups(app)

    print(f"\n{'='*60}")
    print(f"Mise CLI Discovery Report")
    print(f"{'='*60}")
    print(f"\nGroups: {', '.join(groups) if groups else 'None'}")
    print(f"\nCommands ({len(commands)} total):\n")

    current_group = None
    for cmd in sorted(commands, key=lambda c: (c.group or "", c.name)):
        if cmd.group != current_group:
            current_group = cmd.group
            group_label = current_group if current_group else "(top-level)"
            print(f"\n  [{group_label}]")

        help_preview = cmd.help_text[:60] + "..." if len(cmd.help_text) > 60 else cmd.help_text
        print(f"    {cmd.full_path:30s} {help_preview}")

    print(f"\n{'='*60}\n")


# ─── Coverage Gate ──────────────────────────────────────────────────────────

# Commands that have dedicated test files/modules.
# When you add a new test module, update this mapping.
TESTED_COMMANDS = {
    "hello",
    "seed",
    "db init",
    "db add",
    "db list",
    "auth register",
    "auth login",
    "auth logout",
    "auth whoami",
    "auth verify",
    "auth resend-verification",
    "profile setup",
    "profile show",
    "profile add-allergy",
    "profile remove-allergy",
    "profile add-dislike",
    "profile remove-dislike",
    "profile like-cuisine",
    "profile unlike-cuisine",
    "profile set-units",
    "profile set-budget",
    "scrape run",
    "scrape list",
    "ai ask",
    "ai categorize",
    "ai summarize",
    "ai providers",
    "ai health",
    "plan breakfast",
    "plan lunch",
    "plan dinner",
    "plan brunch",
    "plan morning-snack",
    "plan afternoon-snack",
    "plan week",
    "plan day",
    "plan suggest",
    "plan show",
    "plan clear",
    "plan status",
}


def find_uncovered_commands(app: typer.Typer) -> list[CommandInfo]:
    """Find commands that don't have dedicated tests.

    Returns a list of CommandInfo objects for commands not in TESTED_COMMANDS.
    """
    all_commands = discover_commands(app)
    uncovered = [cmd for cmd in all_commands if cmd.full_path not in TESTED_COMMANDS]
    return uncovered


def check_coverage(app: typer.Typer) -> dict:
    """Check test coverage for all CLI commands.

    Returns a dict with:
        - 'total': total number of commands
        - 'covered': number of commands with tests
        - 'uncovered': list of uncovered CommandInfo objects
        - 'coverage_pct': percentage of commands covered
    """
    all_commands = discover_commands(app)
    uncovered = find_uncovered_commands(app)
    covered_count = len(all_commands) - len(uncovered)

    return {
        "total": len(all_commands),
        "covered": covered_count,
        "uncovered": uncovered,
        "coverage_pct": (covered_count / len(all_commands) * 100) if all_commands else 0,
    }