from __future__ import annotations

import ast
from pathlib import Path

ROOTS = ("tests", "packages", "tools")
EXCLUDED_PATH_PARTS = (
    "/build/lib/",
    "/__pycache__/",
)

# Files that define the canonical helper APIs are allowed to use low-level I/O.
ALLOWED_LOW_LEVEL_FILES = {
    "packages/core/providence_core/src/providence_core/utils/text_io.py",
    "tests/helpers/text_io.py",
    "tools/ci/check_text_io_centralization.py",
}


def _is_excluded(path: Path) -> bool:
    as_posix = path.as_posix()
    return any(part in as_posix for part in EXCLUDED_PATH_PARTS)


def _is_allowed(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root).as_posix()
    return rel in ALLOWED_LOW_LEVEL_FILES


def main() -> int:  # noqa: C901
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []

    for root_name in ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if _is_excluded(py_file) or _is_allowed(py_file, repo_root):
                continue

            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                violations.append(f"{py_file}: syntax-error while scanning ({exc})")
                continue

            rel = py_file.relative_to(repo_root).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    violations.append(f"{rel}:{node.lineno}: direct open()")
                    continue

                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "read_text",
                    "write_text",
                }:
                    violations.append(
                        f"{rel}:{node.lineno}: direct Path.{node.func.attr}()"
                    )

    if violations:
        print("Text I/O centralization policy failed.")
        print("Use centralized helpers instead of direct text I/O calls:")
        for item in violations:
            print(f" - {item}")
        return 1

    print("Text I/O centralization policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
