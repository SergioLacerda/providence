from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path("tools/architecture/validate_class_size.py")
    spec = importlib.util.spec_from_file_location("validate_class_size", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mk_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return tmp_path


def _write_class(repo: Path, rel: str, class_name: str, body_lines: int) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join("    x = 1" for _ in range(body_lines))
    path.write_text(f"class {class_name}:\n{body}\n", encoding="utf-8")


def test_class_at_limit_passes(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_class(
        repo,
        "packages/core/providence_core/src/providence_core/limit_case.py",
        "LimitCase",
        399,
    )  # class size = 400 lines (including class line)
    report = validate_class_size._scan_classes(repo, 400, {})
    assert report["ok"] is True


def test_class_above_limit_fails(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_class(
        repo,
        "packages/core/providence_core/src/providence_core/too_big.py",
        "TooBig",
        400,
    )  # class size = 401
    report = validate_class_size._scan_classes(repo, 400, {})
    assert report["ok"] is False
    assert report["violations_count"] == 1


def test_allowlist_skips_violation(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    rel = "packages/core/providence_core/src/providence_core/allowed.py"
    _write_class(repo, rel, "AllowedBig", 500)
    allowlist_path = repo / "tools" / "architecture" / "class_size_allowlist.json"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(
        json.dumps(
            {
                "allowlist": {
                    f"{rel}:AllowedBig": "temporary exception",
                }
            }
        ),
        encoding="utf-8",
    )
    allowlist = validate_class_size._load_allowlist(repo)
    report = validate_class_size._scan_classes(repo, 400, allowlist)
    assert report["ok"] is True


def test_allowlist_windows_separator_is_normalized(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    rel = "packages/core/providence_core/src/providence_core/allowed_windows.py"
    _write_class(repo, rel, "AllowedWindows", 500)
    allowlist_path = repo / "tools" / "architecture" / "class_size_allowlist.json"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(
        json.dumps(
            {
                "allowlist": {
                    "packages\\core\\providence_core\\src\\providence_core\\allowed_windows.py:AllowedWindows": "windows-style path",
                }
            }
        ),
        encoding="utf-8",
    )
    allowlist = validate_class_size._load_allowlist(repo)
    report = validate_class_size._scan_classes(repo, 400, allowlist)
    assert report["ok"] is True


def _write_module(repo: Path, rel: str, line_count: int) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"x{i} = 1" for i in range(line_count)) + "\n", encoding="utf-8"
    )


def test_module_above_limit_fails(tmp_path: Path) -> None:
    """ADR-019: module-size violations are blocking, unlike the pre-ADR-019 warn-only behavior."""
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo, "packages/core/providence_core/src/providence_core/too_big_module.py", 500
    )
    report = validate_class_size._scan_modules(repo, 400, {})
    assert report["ok"] is False
    assert report["warnings_count"] == 1


def test_module_allowlist_grandfathers_violation(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    rel = "packages/core/providence_core/src/providence_core/grandfathered_module.py"
    _write_module(repo, rel, 500)
    allowlist_path = repo / "tools" / "architecture" / "module_size_allowlist.json"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(
        json.dumps({"allowlist": {rel: "ADR-019 grandfathered"}}),
        encoding="utf-8",
    )
    allowlist = validate_class_size._load_module_allowlist(repo)
    report = validate_class_size._scan_modules(repo, 400, allowlist)
    assert report["ok"] is True
    assert report["warnings"] == []


def test_build_directory_excluded_from_module_scan(tmp_path: Path) -> None:
    """Regression: gitignored build/ output must not be scanned as source (ADR-019)."""
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/interfaces/providence_cli/build/lib/providence_cli/commands/docs.py",
        500,
    )
    report = validate_class_size._scan_modules(repo, 400, {})
    assert report["ok"] is True
    assert report["warnings"] == []


def test_build_directory_excluded_from_class_scan(tmp_path: Path) -> None:
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_class(
        repo,
        "packages/interfaces/providence_cli/build/lib/providence_cli/commands/governance.py",
        "TooBigInBuild",
        400,
    )
    report = validate_class_size._scan_classes(repo, 400, {})
    assert report["ok"] is True
    assert report["violations_count"] == 0


def test_builders_directory_is_not_excluded(tmp_path: Path) -> None:
    """The 'build' exclusion is an exact path-segment match, not a substring —
    a real source path like .../builders/pipeline_builder.py must still be scanned."""
    validate_class_size = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/features/providence_integration/src/providence_integration/builders/governance/pipeline_builder.py",
        500,
    )
    report = validate_class_size._scan_modules(repo, 400, {})
    assert report["ok"] is False
    assert report["warnings_count"] == 1
