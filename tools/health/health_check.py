#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Providence Architecture — Health Check Engine."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class HealthCheckEngine:
    """Core health check validator for the Providence monorepo."""

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
            "checks": {},
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "status": "UNKNOWN",
        }

    def _find_project_root(self) -> Path:
        current = Path(__file__).resolve()
        for candidate in [current.parent, *current.parents]:
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "packages"
            ).is_dir():
                return candidate
        raise RuntimeError(
            "Could not locate project root from tools/health/health_check.py. "
            "Expected pyproject.toml + packages/ in a parent directory."
        )

    def _record(self, name: str, passed: bool, msg: str) -> None:
        self.results["checks"][name] = {
            "status": "PASS" if passed else "FAIL",
            "message": msg,
        }
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        if self.verbose:
            tag = "OK  " if passed else "FAIL"
            print(f"  {tag} {name}: {msg}")

    # ── Individual checks ────────────────────────────────────────────────────

    def check_git_status(self) -> tuple[bool, str]:
        try:
            from providence_core.utils.process import SafeProcessRunner

            r = SafeProcessRunner().run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                timeout=5,
            )
            return (
                r.returncode == 0,
                (
                    "Git repository is healthy"
                    if r.returncode == 0
                    else "Not a git repository"
                ),
            )
        except Exception as e:
            return False, f"Git check failed: {e}"

    def check_packages_structure(self) -> tuple[bool, str]:
        required = ["core", "features", "interfaces"]
        packages_dir = self.project_root / "packages"
        missing = [s for s in required if not (packages_dir / s).is_dir()]
        if missing:
            return False, f"Missing package layers: {', '.join(missing)}"
        return True, "Package structure is valid (core, features, interfaces)"

    def check_python_version(self) -> tuple[bool, str]:
        v = sys.version_info
        ok = v.major == 3 and v.minor >= 10
        return (
            ok,
            f"Python {v.major}.{v.minor}.{v.micro} ({'OK' if ok else 'requires 3.10+'})",
        )

    def check_governance_compiled(self) -> tuple[bool, str]:
        compiled = self.project_root / ".providence" / "compiled"
        if not compiled.is_dir():
            return (
                False,
                ".providence/compiled/ not found — run: providence governance compile",
            )
        artifacts = list(compiled.glob("*.msgpack")) + list(compiled.glob("*.json"))
        if not artifacts:
            return (
                False,
                ".providence/compiled/ is empty — run: providence governance compile",
            )
        return True, f".providence/compiled/ has {len(artifacts)} artifact(s)"

    def check_venv(self) -> tuple[bool, str]:
        venv = self.project_root / ".venv"
        if not venv.is_dir():
            return False, ".venv not found — run: ./setup.sh"
        providence_bin = venv / "bin" / "providence"
        if providence_bin.exists():
            return True, ".venv exists and providence CLI is installed"
        return True, ".venv exists (providence CLI not yet installed)"

    def check_docs_structure(self) -> tuple[bool, str]:
        docs = self.project_root / "docs" / "spec" / "canonical"
        if not docs.is_dir():
            return False, "docs/spec/canonical/ not found"
        return True, "Governance docs structure exists"

    # ── Orchestration ────────────────────────────────────────────────────────

    def run_all_checks(self) -> dict[str, Any]:
        checks = [
            ("Git Status", self.check_git_status),
            ("Package Structure", self.check_packages_structure),
            ("Python Version", self.check_python_version),
            ("Compiled Governance", self.check_governance_compiled),
            ("Virtual Environment", self.check_venv),
            ("Docs Structure", self.check_docs_structure),
        ]
        for name, fn in checks:
            passed, msg = fn()
            self._record(name, passed, msg)

        self.results["status"] = (
            "OPERATIONAL" if self.results["summary"]["failed"] == 0 else "FAILED"
        )
        return self.results


if __name__ == "__main__":
    engine = HealthCheckEngine(verbose="--verbose" in sys.argv or "-v" in sys.argv)
    res = engine.run_all_checks()

    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
    else:
        print(f"\nOverall Status: {res['status']}")
        print(f"Project Root:   {res['project_root']}\n")
        for name, check in res["checks"].items():
            tag = "PASS" if check["status"] == "PASS" else "FAIL"
            print(f"  {tag}  {name}: {check['message']}")
        s = res["summary"]
        print(f"\n  {s['passed']}/{s['total']} checks passed")

    sys.exit(0 if res["summary"]["failed"] == 0 else 1)
