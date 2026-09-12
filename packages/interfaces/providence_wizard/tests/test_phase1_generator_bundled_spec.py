"""Regression tests: fresh-workspace bootstrap must load the full bundled
canonical mandate/guideline set, not the single-mandate onboarding stub."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.wizard.phase1_generator import Phase1Generator


def test_fresh_workspace_resolves_full_bundled_mandate_set(tmp_path: Path) -> None:
    """A workspace with no docs-meta and no .providence/source must still bootstrap
    the full mandate/guideline set from the packaged canonical spec, not a
    single-mandate placeholder stub."""
    output_path = tmp_path / "build" / "phase-1-choices"

    generator = Phase1Generator(
        core_path=tmp_path / "packages",
        output_path=output_path,
        config={"adoption_level": "FULL"},
    )
    result = generator.run()

    assert result["success"] is True
    assert result["mandate_count"] > 1
    assert result["guideline_count"] > 1
    descriptions = [m["description"] for m in result["mandates"]]
    assert all(d and d != "No description available" for d in descriptions)


def test_fresh_workspace_full_adoption_level_loads_every_bundled_mandate(
    tmp_path: Path,
) -> None:
    """adoption_level=FULL must not filter the bundled canonical mandate set
    (no selector_selection means no filtering step runs at all)."""
    output_path = tmp_path / "build" / "phase-1-choices"

    generator = Phase1Generator(
        core_path=tmp_path / "packages",
        output_path=output_path,
        config={"adoption_level": "FULL"},
    )
    generator.parse_mandate_spec()
    generator.parse_guidelines_dsl()

    bundled_mandate_spec = generator.resolved_source_files["mandate.spec"]
    from providence_wizard.orchestration.wizard.spec_parser import MandateSpecParser

    all_mandates = MandateSpecParser().parse(
        bundled_mandate_spec.read_text(encoding="utf-8"), is_markdown=False
    )
    assert len(generator.mandates) == len(all_mandates)
