from __future__ import annotations

import re
from pathlib import Path

BLOCKED_PATTERNS = (
    re.compile(r"(^|[^A-Za-z0-9_])\.ai(/|\\|$)"),
    re.compile(r"(^|[^A-Za-z0-9_])\.ia(/|\\|$)"),
)

ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "build",
    "dist",
    # Archival planning/design docs: describe legacy paths as historical context,
    # not as active paths to be created.
    "done",
    "superpowers",
    # Legacy template directory itself — files inside .ai/ are the old artifact.
    ".ai",
    # setuptools build artifacts — auto-generated, not source of truth.
    "egg-info",
}


def _scan_file(path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []
    violations: list[str] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        if "legacy-path-ok" in line:
            continue
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(line):
                violations.append(f"{path}:{idx}: {line.strip()}")
                break
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        # Do not scan this guard itself to avoid self-trigger loops on docs/examples.
        if path.name == "check_no_legacy_ai_paths.py":
            continue
        violations.extend(_scan_file(path))

    if violations:
        print("Legacy path guard failed. Found forbidden legacy references (.ai/.ia):")
        for item in violations:
            print(f" - {item}")
        print("Use '.providence' as single source of truth.")
        return 1

    print("Legacy path guard passed: no '.ai' or '.ia' references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
