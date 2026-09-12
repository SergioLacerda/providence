from __future__ import annotations

import re
from pathlib import Path

# Block bypass for mandatory governance compliance verification commands.
_BYPASS_PATTERNS = (
    re.compile(r"tools/governance/compliance\.py\s+[^\n]*--verify[^\n]*\|\|\s*true"),
    re.compile(
        r"python(?:3)?\s+-m\s+providence_cli\s+governance\s+audit[^\n]*\|\|\s*true"
    ),
)


def _scan_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        for pattern in _BYPASS_PATTERNS:
            if pattern.search(line):
                violations.append(f"{path}:{idx}: {line.strip()}")
                break
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    workflows_dir = root / ".github" / "workflows"

    violations: list[str] = []
    if workflows_dir.exists():
        for path in workflows_dir.rglob("*.yml"):
            violations.extend(_scan_file(path))
        for path in workflows_dir.rglob("*.yaml"):
            violations.extend(_scan_file(path))

    if violations:
        print("Compliance bypass policy failed. Found forbidden '|| true' usage:")
        for item in violations:
            print(f" - {item}")
        print("Mandatory governance compliance checks must fail-closed in CI.")
        return 1

    print("Compliance bypass policy passed: no forbidden governance bypass found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
