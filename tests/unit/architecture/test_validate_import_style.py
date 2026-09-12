from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("tools/architecture/validate_import_style.py")
    spec = importlib.util.spec_from_file_location("validate_import_style", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mk_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "packages").mkdir()
    return tmp_path


def _write_module(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_single_import_style_is_allowed(tmp_path: Path) -> None:
    validate_import_style = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import providence_core.b\n",
    )

    violations, parse_errors = validate_import_style.validate(repo)

    assert violations == []
    assert parse_errors == []


def test_mixed_import_style_for_same_module_is_reported(tmp_path: Path) -> None:
    validate_import_style = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/a.py",
        "import providence_core.b\nfrom providence_core.b import Thing\n",
    )

    violations, parse_errors = validate_import_style.validate(repo)

    assert parse_errors == []
    assert len(violations) == 1
    assert (
        violations[0].path == "packages/core/providence_core/src/providence_core/a.py"
    )
    assert violations[0].module == "providence_core.b"
    assert violations[0].import_lines == (1,)
    assert violations[0].import_from_lines == (2,)


def test_relative_import_from_is_resolved_for_package_modules(tmp_path: Path) -> None:
    validate_import_style = _load_module()
    repo = _mk_repo(tmp_path)
    _write_module(
        repo,
        "packages/core/providence_core/src/providence_core/sub/a.py",
        "import providence_core.sub.b\nfrom .b import Thing\n",
    )

    violations, parse_errors = validate_import_style.validate(repo)

    assert parse_errors == []
    assert len(violations) == 1
    assert violations[0].module == "providence_core.sub.b"
