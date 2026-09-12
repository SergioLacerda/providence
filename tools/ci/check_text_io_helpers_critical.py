from __future__ import annotations

import ast
from pathlib import Path

CRITICAL_FILES = (
    "packages/interfaces/providence_wizard/src/providence_wizard/orchestration/seedlings/ai_seeds.py",
    "tests/integration/wizard/test_seedlings_e2e.py",
    "packages/interfaces/providence_cli/tests/test_governance_output_snapshots.py",
    "packages/core/providence_core/tests/execution/test_guardrail_code_review.py",
)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    violations: list[str] = []

    for rel_path in CRITICAL_FILES:
        path = root / rel_path
        if not path.exists():
            violations.append(f"{rel_path}: file missing")
            continue

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "read_text",
                    "write_text",
                }:
                    violations.append(
                        f"{rel_path}:{node.lineno}: direct {node.func.attr} call in critical path"
                    )
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    violations.append(
                        f"{rel_path}:{node.lineno}: direct open() call in critical path"
                    )

    if violations:
        print("Critical helper policy failed:")
        for item in violations:
            print(f" - {item}")
        print("Use centralized text I/O helpers in critical cross-platform paths.")
        return 1

    print("Critical helper policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
