#!/usr/bin/env python3
"""
Providence Architecture — Diagnostic Test Suite

Runs critical checks across file structure, configuration, imports, and git.

Usage:
    python tools/testing/diagnostics.py [--verbose] [--json]
"""

import importlib
import json
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


class DiagnosticTestSuite:
    """Comprehensive diagnostic test runner."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.project_root = self._find_project_root()
        providence_core_src = (
            self.project_root / "packages" / "core" / "providence_core" / "src"
        )
        if str(providence_core_src) not in sys.path:
            sys.path.insert(0, str(providence_core_src))
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        }
        self._counter = 0

    def _find_project_root(self) -> Path:
        for candidate in [Path.cwd(), *Path.cwd().parents]:
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "packages"
            ).is_dir():
                return candidate
        # Fallback: two levels up from tools/testing/
        return Path(__file__).resolve().parents[2]

    def _run(
        self,
        name: str,
        fn: Callable[[], tuple[bool, str]],
        category: str = "general",
        optional: bool = False,
    ) -> bool:
        self._counter += 1
        try:
            passed, message = fn()
        except Exception as e:
            passed, message = False, f"Exception: {e}"

        # Optional checks that fail are recorded as skipped, not failed
        if not passed and optional:
            status = "SKIP"
            self.results["summary"]["skipped"] += 1
        else:
            status = "PASS" if passed else "FAIL"
            if passed:
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1

        self.results["tests"].append(
            {
                "id": self._counter,
                "name": name,
                "category": category,
                "status": status,
                "message": message,
            }
        )
        self.results["summary"]["total"] += 1

        if self.verbose:
            print(f"  {status:4}  {name}: {message}")

        return passed or optional

    # ── Structure tests ──────────────────────────────────────────────────────

    def _check_packages_root(self) -> tuple[bool, str]:
        d = self.project_root / "packages"
        return d.is_dir(), f"{'Found' if d.is_dir() else 'Not found'} at {d}"

    def _check_packages_subsystems(self) -> tuple[bool, str]:
        required = ["core", "features", "interfaces"]
        missing = [
            s for s in required if not (self.project_root / "packages" / s).is_dir()
        ]
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        return True, f"All {len(required)} subsystems present"

    def _check_docs_root(self) -> tuple[bool, str]:
        d = self.project_root / "docs"
        return d.is_dir(), f"{'Found' if d.is_dir() else 'Not found'} at {d}"

    def _check_governance_compiled(self) -> tuple[bool, str]:
        d = self.project_root / ".providence" / "compiled"
        if not d.is_dir():
            return (
                False,
                ".providence/compiled/ not initialized — run: providence governance compile",
            )
        artifacts = list(d.glob("*.msgpack")) + list(d.glob("*.json"))
        return True, f"{len(artifacts)} artifact(s) in .providence/compiled/"

    def _check_git_dir(self) -> tuple[bool, str]:
        d = self.project_root / ".git"
        return d.exists(), (
            "Git repository initialized" if d.exists() else "Git not initialized"
        )

    def _check_ai_seedling_dirs(self) -> tuple[bool, str]:
        dirs = [".github", ".vscode", ".cursor", ".claude", ".gemini"]
        found = [d for d in dirs if (self.project_root / d).is_dir()]
        if found:
            return True, f"Found {len(found)} AI config dir(s): {', '.join(found)}"
        return (
            False,
            "No AI seedling directories found (.github, .claude, .cursor, etc.)",
        )

    # ── Config tests ─────────────────────────────────────────────────────────

    def _check_tools_scripts(self) -> tuple[bool, str]:
        scripts: list[str] = [
            "tools/health/health_check.py",
            "tools/governance/agent_confidence.py",
            "tools/governance/agent_handshake.py",
            "tools/testing/diagnostics.py",
            "tools/testing/run-all-tests.py",
            "tools/quiz/quiz_executor.py",
        ]
        missing = [s for s in scripts if not (self.project_root / s).is_file()]
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        return True, f"All {len(scripts)} tool scripts present"

    def _check_claude_md(self) -> tuple[bool, str]:
        f = self.project_root / "CLAUDE.md"
        return f.is_file(), (
            "CLAUDE.md found"
            if f.is_file()
            else "CLAUDE.md missing — run: providence governance generate"
        )

    def _check_copilot_instructions(self) -> tuple[bool, str]:
        f = self.project_root / ".github" / "copilot-instructions.md"
        return f.is_file(), (
            "copilot-instructions.md found"
            if f.is_file()
            else "Missing — run: providence governance generate"
        )

    # ── Import tests ─────────────────────────────────────────────────────────

    def _check_import(self, module: str) -> tuple[bool, str]:
        # Add tools/ to path so tools.* imports resolve
        tools_root = str(self.project_root)
        if tools_root not in sys.path:
            sys.path.insert(0, tools_root)
        try:
            importlib.import_module(module)
            return True, f"{module} imports successfully"
        except Exception as e:
            return False, f"Import error: {e}"

    # ── Git tests ────────────────────────────────────────────────────────────

    def _check_git_status(self) -> tuple[bool, str]:
        try:
            from providence_core.utils.process import SafeProcessRunner

            r = SafeProcessRunner().run(
                ["git", "status"],
                cwd=self.project_root,
                capture_output=True,
                timeout=5,
            )
            return r.returncode == 0, (
                "Repository is readable" if r.returncode == 0 else "git status failed"
            )
        except Exception as e:
            return False, f"Git error: {e}"

    def _check_git_main_branch(self) -> tuple[bool, str]:
        try:
            from providence_core.utils.process import SafeProcessRunner

            r = SafeProcessRunner().run(
                ["git", "branch", "--list", "main"],
                cwd=self.project_root,
                capture_output=True,
                timeout=5,
            )
            if "main" in r.stdout:
                return True, "main branch exists"
            return False, "main branch not found"
        except Exception as e:
            return False, f"Git branch check error: {e}"

    # ── Orchestration ─────────────────────────────────────────────────────────

    def run_all(self) -> dict[str, Any]:
        # Structure
        self._run("packages/ directory", self._check_packages_root, "structure")
        self._run(
            "Package subsystems (core/features/interfaces)",
            self._check_packages_subsystems,
            "structure",
        )
        self._run("docs/ root", self._check_docs_root, "structure")
        self._run(
            "Compiled governance (.providence/compiled/)",
            self._check_governance_compiled,
            "structure",
            optional=True,
        )
        self._run("Git directory", self._check_git_dir, "structure")
        self._run(
            "AI seedling directories",
            self._check_ai_seedling_dirs,
            "structure",
            optional=True,
        )

        # Config
        self._run("Tool scripts", self._check_tools_scripts, "config")
        self._run("CLAUDE.md", self._check_claude_md, "config", optional=True)
        self._run(
            "Copilot instructions",
            self._check_copilot_instructions,
            "config",
            optional=True,
        )

        # Imports
        self._run(
            "Import tools.health.health_check",
            lambda: self._check_import("tools.health.health_check"),
            "import",
        )
        self._run(
            "Import tools.governance.agent_confidence",
            lambda: self._check_import("tools.governance.agent_confidence"),
            "import",
        )
        self._run(
            "Import tools.testing.diagnostics",
            lambda: self._check_import("tools.testing.diagnostics"),
            "import",
        )

        # Git
        self._run("Git repository readable", self._check_git_status, "git")
        self._run("main branch exists", self._check_git_main_branch, "git")

        return self.results

    def print_report(self) -> None:
        print(f"\n{'=' * 70}")
        print("Providence Diagnostic Report")
        print(f"{'=' * 70}\n")

        by_category: dict[str, list[Any]] = {}
        for test in self.results["tests"]:
            by_category.setdefault(test["category"], []).append(test)

        for cat in ["structure", "config", "import", "git"]:
            if cat not in by_category:
                continue
            print(f"[{cat.upper()}]")
            for t in by_category[cat]:
                print(f"  {t['status']:4}  {t['name']}: {t['message']}")
            print()

        s = self.results["summary"]
        pct = int(s["passed"] / s["total"] * 100) if s["total"] else 0
        print(
            f"Summary: {s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped / {s['total']} total ({pct}%)"
        )
        status = "ALL CHECKS PASSED" if s["failed"] == 0 else "SOME CHECKS FAILED"
        print(f"Status:  {status}")
        print("=" * 70)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Providence Diagnostic Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    suite = DiagnosticTestSuite(verbose=args.verbose)
    results = suite.run_all()

    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        suite.print_report()

    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
