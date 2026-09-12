#!/usr/bin/env python3
"""
Architecture health score — runs lint, type checks, and tests in parallel.

Score starts at 100 and deductions are applied per failing check.
Output is a JSON report: {"score": int, "results": {name: "ok"|"fail"|"error"}}.

Exit code:
  0  all checks pass
  1  one or more checks failed
"""

import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path

# Repo root (two levels up from tools/architecture/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = _REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))

# (command, penalty_points, label)
# penalty_points are deducted from 100 when the check fails.
CHECKS: tuple[tuple[Sequence[str], int, str], ...] = (
    (
        [sys.executable, "-m", "ruff", "check", "packages/", "tools/"],
        20,
        "lint",
    ),
    (
        [sys.executable, "-m", "mypy", "--ignore-missing-imports", "packages/"],
        20,
        "types",
    ),
    (
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit",
            "tests/integration",
            "-q",
            "--tb=short",
        ],
        30,
        "tests",
    ),
)

_TIMEOUT = 120  # seconds per check


async def _run(cmd: Sequence[str]) -> tuple[int, str, str]:
    """Run governed process and return (returncode, stdout, stderr)."""

    def _invoke() -> tuple[int, str, str]:
        from providence_core.utils.process import ProcessTimeoutError, SafeProcessRunner

        runner = SafeProcessRunner()
        try:
            result = runner.run(
                list(cmd),
                cwd=_REPO_ROOT,
                capture_output=True,
                timeout=_TIMEOUT,
            )
            return result.returncode, result.stdout, result.stderr
        except ProcessTimeoutError:
            return 1, "", f"TIMEOUT after {_TIMEOUT}s"
        except Exception as exc:
            return 1, "", str(exc)

    return await asyncio.to_thread(_invoke)


async def main() -> None:
    score = 100
    results: dict[str, str] = {}
    has_failure = False

    tasks = [_run(cmd) for cmd, _, _ in CHECKS]
    outcomes = await asyncio.gather(*tasks)

    for (_, penalty, name), (code, stdout, stderr) in zip(
        CHECKS, outcomes, strict=False
    ):
        if code == 0:
            results[name] = "ok"
        else:
            score -= penalty
            results[name] = "fail"
            has_failure = True
            # Show failure output so it's debuggable
            output = (stdout + stderr).strip()
            if output:
                print(f"\n--- {name} FAILED ---", file=sys.stderr)
                # Show up to 40 lines to avoid flooding terminal
                lines = output.splitlines()
                for line in lines[:40]:
                    print(f"  {line}", file=sys.stderr)
                if len(lines) > 40:
                    print(f"  ... ({len(lines) - 40} more lines)", file=sys.stderr)

    report = {"score": max(score, 0), "results": results}
    print(json.dumps(report, indent=2))

    if has_failure:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
