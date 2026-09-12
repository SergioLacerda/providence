from __future__ import annotations

import re
from pathlib import Path

MANDATORY_PATTERNS = (
    re.compile(r"tools/governance/compliance\.py\s+[^\n]*--verify"),
    re.compile(r"python(?:3)?\s+-m\s+providence_cli\s+governance\s+compile"),
    re.compile(r"python(?:3)?\s+-m\s+providence_cli\s+governance\s+validate"),
)

CONTINUE_ON_ERROR_TRUE = re.compile(r"^\s*continue-on-error:\s*true\s*$")
STEP_NAME = re.compile(r"^\s*-\s*name:\s*(.+)$")
RUN_LINE = re.compile(r"^\s*run:\s*\|?\s*(.*)$")


def _scan_workflow(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    violations: list[str] = []

    current_step_name = "<unnamed-step>"
    current_step_start = 0
    current_step_lines: list[str] = []
    current_step_has_continue_true = False

    def flush_step() -> None:
        nonlocal current_step_lines, current_step_has_continue_true
        if not current_step_lines:
            return
        body = "\n".join(current_step_lines)
        is_mandatory = any(p.search(body) for p in MANDATORY_PATTERNS)
        if is_mandatory and current_step_has_continue_true:
            violations.append(
                f"{path}:{current_step_start}: mandatory governance step uses continue-on-error=true ({current_step_name})"
            )
        current_step_lines = []
        current_step_has_continue_true = False

    for idx, line in enumerate(lines, start=1):
        m = STEP_NAME.match(line)
        if m:
            flush_step()
            current_step_name = m.group(1).strip()
            current_step_start = idx
            current_step_lines = [line]
            continue

        if not current_step_lines:
            continue

        current_step_lines.append(line)
        if CONTINUE_ON_ERROR_TRUE.match(line):
            current_step_has_continue_true = True

    flush_step()
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    workflows = root / ".github" / "workflows"
    violations: list[str] = []
    for ext in ("*.yml", "*.yaml"):
        for path in workflows.rglob(ext):
            violations.extend(_scan_workflow(path))

    if violations:
        print("Governance mandatory lanes policy failed:")
        for item in violations:
            print(f" - {item}")
        print("Mandatory compliance/governance steps must be fail-closed.")
        return 1

    print("Governance mandatory lanes policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
