from __future__ import annotations

from pathlib import Path

import pytest

from providence_wizard.orchestration.wizard import phase1_generator
from providence_wizard.orchestration.wizard.phase1_generator import Phase1Generator


@pytest.fixture(autouse=True)
def _no_bundled_spec(monkeypatch):
    """These tests exercise the docs-meta/source_spec fallback tiers, not the
    bundled canonical spec (which now ships real content and would otherwise
    take precedence over the fixtures written by these tests)."""
    monkeypatch.setattr(phase1_generator, "_bundled_spec_dir", lambda: None)


def _write_docs_meta(build_dir: Path) -> None:
    docs_meta = build_dir / "docs-meta"
    docs_meta.mkdir(parents=True)
    (docs_meta / "mandate.spec").write_text(
        """
mandate M001 {
  title: "Clean Architecture"
  description: "Keep domain logic isolated."
  type: "MANDATE"
  category: "core"
  rationale: "Boundary integrity."
}

mandate M002 {
  title: "Test Driven Development"
  description: "Add regression coverage."
  type: "MANDATE"
  category: "core"
  rationale: "Delivery safety."
}
""".strip(),
        encoding="utf-8",
    )
    (docs_meta / "guidelines.dsl").write_text(
        """
guideline G001 {
  title: "Keep functions small"
  description: "Prefer focused units."
  type: "GUIDELINE"
  category: "quality"
}
""".strip(),
        encoding="utf-8",
    )


def test_phase1_generator_filters_mandates_using_selector_selection(
    tmp_path: Path,
) -> None:
    build_dir = tmp_path / "build"
    output_path = build_dir / "phase-1-choices"
    _write_docs_meta(build_dir)

    generator = Phase1Generator(
        core_path=tmp_path / "packages",
        output_path=output_path,
        config={"selector_selection": {"resolved_ids": ["M001"]}},
    )

    result = generator.run()

    assert result["success"] is True
    assert result["mandate_count"] == 1
    content = (output_path / "mandates-core.md").read_text(encoding="utf-8")
    assert "## M001: Clean Architecture" in content
    assert "## M002: Test Driven Development" not in content


def test_phase1_generator_rejects_unknown_selector_ids(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    output_path = build_dir / "phase-1-choices"
    _write_docs_meta(build_dir)

    generator = Phase1Generator(
        core_path=tmp_path / "packages",
        output_path=output_path,
        config={"selector_selection": {"resolved_ids": ["M999"]}},
    )

    result = generator.run()

    assert result["success"] is False
    assert result["error"] == "Unknown selected IDs: M999"
