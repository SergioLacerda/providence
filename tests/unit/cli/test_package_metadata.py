"""Package metadata regressions for the providence-cli distribution."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def test_providence_cli_declares_direct_providence_core_dependency() -> None:
    pyproject = Path("packages/interfaces/providence_cli/pyproject.toml")
    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    dependencies = metadata["project"]["dependencies"]

    assert "providence-core>=1.0" in dependencies
