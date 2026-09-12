from __future__ import annotations

from pathlib import Path

from providence_core.governance.spec_bootstrapper import SourceSpecBootstrapper


def test_bootstrap_source_specs_from_markdown_when_docs_meta_missing(
    tmp_path: Path,
) -> None:
    # Canonical mandate files (with **ID:** M* declarations) are the source of truth
    canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "M001_ARCH.md").write_text(
        "# Mandate: Clean Architecture\n\n**ID:** M001\n", encoding="utf-8"
    )
    (canonical_dir / "M002_TDD.md").write_text(
        "# Mandate: Test-Driven Development\n\n**ID:** M002\n", encoding="utf-8"
    )

    spec_dir = tmp_path / "generated" / "client" / "build" / "docs-meta"
    bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)

    bootstrapper.bootstrap()

    mandate_spec = spec_dir / "mandate.md"
    guidelines_dsl = spec_dir / "guidelines.dsl"

    assert mandate_spec.exists()
    assert guidelines_dsl.exists()
    assert "M001" in mandate_spec.read_text(encoding="utf-8")
    assert "M002" in mandate_spec.read_text(encoding="utf-8")
    content = guidelines_dsl.read_text(encoding="utf-8")
    assert "guideline G021" in content
    assert "guideline G022" in content
    assert "guideline G001" not in content
