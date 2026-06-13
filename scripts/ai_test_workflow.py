#!/usr/bin/env python3
"""AI Testing Workflow — Dynamic exploratory testing driven by an AI agent.

This script is designed to be run by an AI agent (like Cline) that can:
1. Discover all CLI commands automatically
2. Execute them with various inputs
3. Evaluate results intelligently (not just pass/fail)
4. Generate a narrative report

Unlike pytest which uses mocked AI, this script uses REAL AI providers
because the AI agent itself can generate and evaluate responses.

Usage:
    python scripts/ai_test_workflow.py [--discover] [--report REPORT_PATH]

The --discover flag just prints all discovered commands.
The --report flag specifies where to save the markdown report.
"""

from __future__ import annotations

import os
import sys
import subprocess
import json
import tempfile
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@dataclass
class TestResult:
    """Result of a single test command execution."""
    command: str
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    notes: str = ""
    duration_ms: float = 0


@dataclass
class WorkflowReport:
    """Complete report of the AI testing workflow."""
    timestamp: str
    total_commands: int
    tested_commands: int
    passed: int
    failed: int
    errors: int
    results: list[TestResult] = field(default_factory=list)
    summary: str = ""
    ai_observations: list[str] = field(default_factory=list)


class AITestWorkflow:
    """Dynamic exploratory testing workflow for the Mise CLI app."""

    def __init__(self):
        self.results: list[TestResult] = []
        self.observations: list[str] = []
        self.report_dir = PROJECT_ROOT / "test_reports"
        self.report_dir.mkdir(exist_ok=True)

    def _run_mise(self, args: list[str], input_text: str = None, timeout: int = 30) -> TestResult:
        """Run a mise CLI command and capture the result.

        Args:
            args: Command-line arguments (e.g., ["auth", "register", "--username", "test"])
            input_text: Optional stdin input for interactive commands
            timeout: Timeout in seconds

        Returns:
            TestResult with exit code, output, and timing
        """
        import time
        cmd = ["mise"] + args
        start = time.time()

        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "DATABASE_URL": "sqlite:///test_workflow.db", "EMAIL_VERIFICATION_REQUIRED": "false"},
            )
            duration = (time.time() - start) * 1000

            return TestResult(
                command=" ".join(args),
                args=args,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                command=" ".join(args),
                args=args,
                exit_code=-1,
                stdout="",
                stderr="Command timed out",
                success=False,
                notes="TIMEOUT",
                duration_ms=timeout * 1000,
            )
        except Exception as e:
            return TestResult(
                command=" ".join(args),
                args=args,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                success=False,
                notes=f"EXCEPTION: {type(e).__name__}",
            )

    def _note(self, observation: str):
        """Record an observation about the test."""
        self.observations.append(observation)

    # ─── Discovery ──────────────────────────────────────────────────────────

    def discover_commands(self) -> list[dict]:
        """Discover all CLI commands by running --help and parsing output."""
        from mise.cli.main import app
        from tests.e2e.discovery import discover_commands, print_discovery

        commands = discover_commands(app)
        print_discovery(app)
        return [{"name": c.name, "full_path": c.full_path, "group": c.group, "help_text": c.help_text} for c in commands]

    # ─── Test Scenarios ─────────────────────────────────────────────────────

    def test_smoke_commands(self) -> list[TestResult]:
        """Test basic commands that don't require auth or data."""
        print("\n🔍 Testing smoke commands...")

        # hello
        r = self._run_mise(["hello"])
        self._note(f"hello command: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # hello with custom text
        r = self._run_mise(["hello", "--text", "AI Testing"])
        self._note(f"hello --text: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # db init
        r = self._run_mise(["db", "init"])
        self._note(f"db init: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # seed
        r = self._run_mise(["seed"])
        self._note(f"seed: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # db list (should show seeded data)
        r = self._run_mise(["db", "list"])
        self._note(f"db list (with data): {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        return self.results[-5:]

    def test_auth_flow(self) -> list[TestResult]:
        """Test authentication: register, login, whoami, logout."""
        print("\n🔐 Testing auth flow...")

        # Register
        r = self._run_mise(["auth", "register", "--username", "ai_test_user", "--email", "ai@test.com", "--password", "AiTest123!"])
        self._note(f"auth register: {'PASS' if r.success else 'FAIL'} — {r.stdout[:100]}")
        self.results.append(r)

        # Login
        r = self._run_mise(["auth", "login", "--username", "ai_test_user", "--password", "AiTest123!"])
        self._note(f"auth login: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Whoami
        r = self._run_mise(["auth", "whoami"])
        self._note(f"auth whoami: {'PASS' if r.success else 'FAIL'} — {r.stdout[:100]}")
        self.results.append(r)

        # Logout
        r = self._run_mise(["auth", "logout"])
        self._note(f"auth logout: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        return self.results[-4:]

    def test_profile_flow(self) -> list[TestResult]:
        """Test profile setup and preferences."""
        print("\n👤 Testing profile flow...")

        # Login first
        r = self._run_mise(["auth", "login", "--username", "ai_test_user", "--password", "AiTest123!"])
        self.results.append(r)

        # Add allergy
        r = self._run_mise(["profile", "add-allergy", "peanuts"])
        self._note(f"add allergy: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Like cuisine
        r = self._run_mise(["profile", "like-cuisine", "Italian"])
        self._note(f"like cuisine: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Set budget
        r = self._run_mise(["profile", "set-budget", "75"])
        self._note(f"set budget: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Set units
        r = self._run_mise(["profile", "set-units", "metric"])
        self._note(f"set units: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Show profile
        r = self._run_mise(["profile", "show"])
        self._note(f"profile show: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        return self.results[-6:]

    def test_discount_flow(self) -> list[TestResult]:
        """Test discount database operations."""
        print("\n💰 Testing discount flow...")

        # Add a discount
        r = self._run_mise(["db", "add", "--store", "AI Test Store", "--product", "AI Test Product", "--category", "Test", "--original-price", "10.00", "--discount-price", "5.00"])
        self._note(f"db add: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # List all
        r = self._run_mise(["db", "list"])
        self._note(f"db list: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Filter by store
        r = self._run_mise(["db", "list", "--store", "AI Test Store"])
        self._note(f"db list --store: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        # Filter by category
        r = self._run_mise(["db", "list", "--category", "Test"])
        self._note(f"db list --category: {'PASS' if r.success else 'FAIL'}")
        self.results.append(r)

        return self.results[-4:]

    def test_edge_cases(self) -> list[TestResult]:
        """Test edge cases and error handling."""
        print("\n⚠️  Testing edge cases...")

        # Login without registration
        r = self._run_mise(["auth", "login", "--username", "nonexistent", "--password", "wrong"])
        self._note(f"login nonexistent user: {'expected FAIL' if not r.success else 'unexpected PASS'}")
        self.results.append(r)

        # Double logout
        r = self._run_mise(["auth", "logout"])
        r2 = self._run_mise(["auth", "logout"])
        self._note(f"double logout: first={r.success}, second={r2.success}")
        self.results.append(r)
        self.results.append(r2)

        # Invalid meal type
        r = self._run_mise(["plan", "suggest", "--meal", "invalid_meal_type"])
        self._note(f"invalid meal type: {'expected FAIL' if not r.success else 'unexpected PASS'}")
        self.results.append(r)

        # Whoami without login
        r = self._run_mise(["auth", "whoami"])
        self._note(f"whoami without login: output says '{r.stdout[:80]}'")
        self.results.append(r)

        return self.results[-5:]

    # ─── Report Generation ──────────────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a markdown report of all test results."""
        report = WorkflowReport(
            timestamp=datetime.now().isoformat(),
            total_commands=len(self.results),
            tested_commands=len(self.results),
            passed=sum(1 for r in self.results if r.success),
            failed=sum(1 for r in self.results if not r.success),
            errors=sum(1 for r in self.results if r.notes.startswith("EXCEPTION")),
            results=self.results,
            ai_observations=self.observations,
        )

        md = f"""# Mise AI Testing Workflow Report

**Generated:** {report.timestamp}

## Summary

| Metric | Count |
|--------|-------|
| Total Tests | {report.total_commands} |
| Passed | {report.passed} |
| Failed | {report.failed} |
| Errors | {report.errors} |
| Pass Rate | {report.passed / report.total_commands * 100:.1f}% |

## AI Observations

"""
        for obs in report.ai_observations:
            md += f"- {obs}\n"

        md += "\n## Detailed Results\n\n"
        md += "| # | Command | Exit Code | Success | Duration (ms) | Notes |\n"
        md += "|---|---------|-----------|---------|---------------|-------|\n"

        for i, r in enumerate(report.results, 1):
            success_icon = "✅" if r.success else "❌"
            notes = r.notes if r.notes else ""
            md += f"| {i} | `{r.command}` | {r.exit_code} | {success_icon} | {r.duration_ms:.0f} | {notes} |\n"

        md += "\n## Failed Tests Detail\n\n"
        for r in report.results:
            if not r.success:
                md += f"### `{r.command}`\n\n"
                md += f"- **Exit code:** {r.exit_code}\n"
                md += f"- **Duration:** {r.duration_ms:.0f}ms\n"
                md += f"- **Notes:** {r.notes}\n\n"
                md += f"**stdout:**\n```\n{r.stdout[:500]}\n```\n\n"
                md += f"**stderr:**\n```\n{r.stderr[:500]}\n```\n\n"

        return md

    def save_report(self, path: Optional[str] = None) -> str:
        """Save the report to a markdown file."""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(self.report_dir / f"ai_workflow_{timestamp}.md")

        report = self.generate_report()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(report)
        print(f"\n📄 Report saved to: {path}")
        return path

    # ─── Main Runner ────────────────────────────────────────────────────────

    def run_all(self) -> str:
        """Run all test scenarios and generate a report."""
        print("=" * 60)
        print("🤖 Mise AI Testing Workflow")
        print("=" * 60)

        # Setup: initialize test DB
        print("\n📦 Setting up test environment...")
        self._run_mise(["db", "init"])

        # Run all test scenarios
        self.test_smoke_commands()
        self.test_auth_flow()
        self.test_profile_flow()
        self.test_discount_flow()
        self.test_edge_cases()

        # Generate and save report
        report_path = self.save_report()

        # Print summary
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        print(f"\n{'=' * 60}")
        print(f"📊 Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
        print(f"📄 Full report: {report_path}")
        print(f"{'=' * 60}")

        return report_path


def main():
    """Main entry point for the AI testing workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Mise AI Testing Workflow")
    parser.add_argument("--discover", action="store_true", help="Just discover and list all CLI commands")
    parser.add_argument("--report", type=str, default=None, help="Path to save the report markdown file")
    parser.add_argument("--scenario", type=str, default="all",
                       choices=["all", "smoke", "auth", "profile", "discounts", "edge"],
                       help="Which test scenario to run")
    args = parser.parse_args()

    workflow = AITestWorkflow()

    if args.discover:
        commands = workflow.discover_commands()
        print(f"\nDiscovered {len(commands)} commands:")
        for cmd in commands:
            print(f"  {cmd['full_path']:30s} {cmd['help_text'][:60]}")
        return

    if args.scenario == "all":
        workflow.run_all()
    else:
        # Setup
        workflow._run_mise(["db", "init"])

        if args.scenario == "smoke":
            workflow.test_smoke_commands()
        elif args.scenario == "auth":
            workflow.test_auth_flow()
        elif args.scenario == "profile":
            workflow.test_profile_flow()
        elif args.scenario == "discounts":
            workflow.test_discount_flow()
        elif args.scenario == "edge":
            workflow.test_edge_cases()

        workflow.save_report(args.report)


if __name__ == "__main__":
    main()