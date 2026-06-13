"""Test report generator — produces markdown reports from test results.

Usage:
    python -m tests.e2e.reporter [--output REPORT_PATH]

This module provides utilities for generating human-readable test reports
from pytest results. It's also used by the AI testing workflow.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class TestEntry:
    """A single test result entry."""
    name: str
    module: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "ERROR"
    duration_ms: float = 0
    message: str = ""
    output: str = ""


@dataclass
class TestReport:
    """A complete test report."""
    timestamp: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    entries: list[TestEntry] = field(default_factory=list)
    coverage_pct: float = 0
    uncovered_commands: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0


def generate_markdown_report(report: TestReport) -> str:
    """Generate a markdown report from a TestReport."""
    md = f"""# Mise E2E Test Report

**Generated:** {report.timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {report.total} |
| Passed | {report.passed} ✅ |
| Failed | {report.failed} ❌ |
| Skipped | {report.skipped} ⏭️ |
| Errors | {report.errors} 💥 |
| Pass Rate | {report.pass_rate:.1f}% |
| Command Coverage | {report.coverage_pct:.1f}% |

"""

    if report.uncovered_commands:
        md += "## ⚠️ Uncovered Commands\n\n"
        md += "The following CLI commands lack dedicated test coverage:\n\n"
        for cmd in report.uncovered_commands:
            md += f"- `{cmd}`\n"
        md += "\n"

    md += "## Test Results\n\n"
    md += "| # | Test | Module | Status | Duration |\n"
    md += "|---|------|--------|--------|----------|\n"

    for i, entry in enumerate(report.entries, 1):
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌",
            "SKIPPED": "⏭️",
            "ERROR": "💥",
        }.get(entry.status, "?")
        md += f"| {i} | `{entry.name}` | {entry.module} | {status_icon} {entry.status} | {entry.duration_ms:.0f}ms |\n"

    # Failed tests detail
    failed_entries = [e for e in report.entries if e.status in ("FAILED", "ERROR")]
    if failed_entries:
        md += "\n## Failed Tests Detail\n\n"
        for entry in failed_entries:
            md += f"### `{entry.name}`\n\n"
            md += f"- **Module:** {entry.module}\n"
            md += f"- **Status:** {entry.status}\n"
            md += f"- **Duration:** {entry.duration_ms:.0f}ms\n"
            if entry.message:
                md += f"- **Message:** {entry.message}\n"
            if entry.output:
                md += f"\n```\n{entry.output[:1000]}\n```\n"
            md += "\n"

    return md


def save_report(report: TestReport, path: Optional[str] = None) -> str:
    """Save a test report as markdown."""
    if path is None:
        report_dir = PROJECT_ROOT / "test_reports"
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(report_dir / f"e2e_report_{timestamp}.md")

    md = generate_markdown_report(report)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(md)
    return path


def generate_coverage_report() -> TestReport:
    """Generate a coverage report by checking which commands have tests."""
    from mise.cli.main import app
    from tests.e2e.discovery import discover_commands, TESTED_COMMANDS

    commands = discover_commands(app)
    uncovered = [c.full_path for c in commands if c.full_path not in TESTED_COMMANDS]
    coverage_pct = ((len(commands) - len(uncovered)) / len(commands) * 100) if commands else 0

    return TestReport(
        timestamp=datetime.now().isoformat(),
        total=len(commands),
        passed=len(commands) - len(uncovered),
        failed=len(uncovered),
        coverage_pct=coverage_pct,
        uncovered_commands=uncovered,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mise Test Report Generator")
    parser.add_argument("--output", type=str, default=None, help="Output path for the report")
    parser.add_argument("--coverage", action="store_true", help="Generate a coverage report")
    args = parser.parse_args()

    if args.coverage:
        report = generate_coverage_report()
        path = save_report(report, args.output)
        print(f"\n📊 Coverage Report:")
        print(f"   Total commands: {report.total}")
        print(f"   Covered: {report.passed}")
        print(f"   Uncovered: {report.failed}")
        print(f"   Coverage: {report.coverage_pct:.1f}%")
        if report.uncovered_commands:
            print(f"\n   ⚠️  Uncovered commands:")
            for cmd in report.uncovered_commands:
                print(f"      - {cmd}")
        print(f"\n   📄 Report saved to: {path}")
    else:
        print("Use --coverage to generate a coverage report, or use this module from pytest.")