from __future__ import annotations

import re
from pathlib import Path

BLOCKED_PATTERNS = (
    re.compile(r"\buv run sdd\b"),
    re.compile(r"\bsdd\s+(governance|lint|init|docs|tools|runtime|ask|bootstrap)\b"),
)

# Lines carrying this marker exercise the installed client entrypoint on
# purpose (e.g. release install smoke tests) and are exempt from the policy.
ALLOW_MARKER = "sdd-ci-policy: allow-client-smoke"


def _scan_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        if line.strip().startswith("#"):
            # YAML comment, not a shell command GitHub Actions would execute
            # (e.g. prose explaining a `run:` step's behavior in backticks).
            continue
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(line):
                violations.append(f"{path}:{idx}: {line.strip()}")
                break
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    targets = [root / ".github" / "workflows", root / ".github" / "actions"]
    violations: list[str] = []

    for target in targets:
        if not target.exists():
            continue
        for path in target.rglob("*.yml"):
            violations.extend(_scan_file(path))
        for path in target.rglob("*.yaml"):
            violations.extend(_scan_file(path))

    if violations:
        print("CI command policy failed. Found forbidden SDD command usage:")
        for item in violations:
            print(f" - {item}")
        print(
            "Use 'uv run python -m providence_cli ...' or dedicated tools/*.py scripts."
        )
        return 1

    print("CI command policy passed: no forbidden 'sdd' command usage found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
