from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from providence_wizard.orchestration.wizard import (
    _selector_canonical_fallback as canonical_fallback_module,
)
from providence_wizard.orchestration.wizard import (
    selector_compiler as selector_compiler_module,
)
from providence_wizard.orchestration.wizard import (
    selector_compiler_cli as selector_compiler_cli_module,
)
from providence_wizard.orchestration.wizard.selector_compiler import SelectorCompiler


def _write_repo_fixture(
    tmp_path: Path,
    *,
    metadata: dict[str, object],
    mandates_text: str,
) -> Path:
    (tmp_path / ".providence" / "source" / "mandates").mkdir(parents=True)
    (tmp_path / ".providence" / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (tmp_path / ".providence" / "source" / "mandates" / "mandates.md").write_text(
        mandates_text,
        encoding="utf-8",
    )
    return tmp_path


def _write_assets(tmp_path: Path) -> Path:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    for name in (
        "index.html",
        "selector.js",
        "style.css",
        "site-header.js",
        "site-header.css",
    ):
        (asset_dir / name).write_text(name, encoding="utf-8")
    return asset_dir


def test_selector_compiler_builds_payload(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()
    assert payload["version"] == "1.0"
    item = payload["items"][0]
    assert item["id"] == "M001"
    assert item["mandatory"] is True
    assert item["depends_on"] == []


def test_selector_compiler_rejects_duplicate_sections(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

First description.

## M001: Clean Architecture

Second description.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="Duplicate mandate section"):
        compiler.build_payload()


def test_selector_compiler_rejects_unknown_dependencies(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated.

**Depends on:** M999
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="Unknown selector dependency ids: M999"):
        compiler.build_payload()


def test_selector_compiler_build_site_writes_assets(tmp_path: Path) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    output_dir = tmp_path / "site" / "selector"
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    compiler.build_site(output_dir)
    assert (output_dir / "data.json").exists()
    assert (output_dir / "index.html").read_text(encoding="utf-8") == "index.html"


def test_selector_compiler_build_site_with_packaged_assets_has_import_and_export(
    tmp_path: Path,
) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    output_dir = tmp_path / "site" / "selector"
    compiler = SelectorCompiler(repo_root=repo_root)

    compiler.build_site(output_dir)

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    js = (output_dir / "selector.js").read_text(encoding="utf-8")
    assert "Import JSON" in html
    assert "import-file" in html
    assert "function importSelectionFile" in js
    assert "resolved: [...resolved].sort()" in js


# ---------------------------------------------------------------------------
# Guideline support
# ---------------------------------------------------------------------------

_GUIDELINES_DSL = """
guideline G01 {
  type: HARD
  title: "Use typed interfaces"
  description: "All public APIs must use typed interfaces."
  category: quality
  tags: ["typing", "api"]
}

guideline G02 {
  type: SOFT
  title: "Prefer immutable data"
  description: "Prefer immutable data structures where possible."
  category: style
  tags: ["immutability"]
}
""".strip()


def _write_repo_fixture_with_guidelines(
    tmp_path: Path,
    *,
    metadata: dict[str, object],
    mandates_text: str,
    guidelines_dsl: str = _GUIDELINES_DSL,
) -> Path:
    repo_root = _write_repo_fixture(
        tmp_path, metadata=metadata, mandates_text=mandates_text
    )
    (repo_root / ".providence" / "source" / "guidelines.dsl").write_text(
        guidelines_dsl, encoding="utf-8"
    )
    return repo_root


def test_selector_compiler_includes_guideline_items(tmp_path: Path) -> None:
    """Guidelines from DSL are included as separate items with item_type='guideline'."""
    repo_root = _write_repo_fixture_with_guidelines(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    items = payload["items"]
    ids = {item["id"] for item in items}
    assert "M001" in ids
    assert "G01" in ids
    assert "G02" in ids

    g01 = next(i for i in items if i["id"] == "G01")
    assert g01["item_type"] == "guideline"
    assert g01["mandatory"] is True
    assert g01["title"] == "Use typed interfaces"

    g02 = next(i for i in items if i["id"] == "G02")
    assert g02["item_type"] == "guideline"
    assert g02["mandatory"] is False


def test_selector_compiler_mandate_item_type_is_mandate(tmp_path: Path) -> None:
    """Mandate items always carry item_type='mandate'."""
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    m001 = next(i for i in payload["items"] if i["id"] == "M001")
    assert m001["item_type"] == "mandate"


def test_selector_compiler_mixed_payload_no_duplicate_ids(tmp_path: Path) -> None:
    """Mixed mandate+guideline payload has no duplicate IDs."""
    repo_root = _write_repo_fixture_with_guidelines(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture", "M002": "Testing"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.

## M002: Testing

All changes must include tests.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert len(ids) == len(set(ids)), "Duplicate IDs in mixed payload"
    assert set(ids) == {"M001", "M002", "G01", "G02"}


def test_selector_compiler_no_guidelines_dsl_omits_guideline_items(
    tmp_path: Path,
) -> None:
    """When guidelines.dsl is absent, only mandates are included."""
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert ids == ["M001"]


# ---------------------------------------------------------------------------
# Fallback paths: no .providence artifacts
# ---------------------------------------------------------------------------


def test_selector_compiler_no_sdd_and_no_canonical_docs_returns_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When neither .providence nor docs/spec/canonical exist, items are empty and a WARN is printed."""
    compiler = SelectorCompiler(repo_root=tmp_path)

    payload = compiler.build_payload()

    assert payload["items"] == []
    captured = capsys.readouterr()
    assert "WARN: governance artifacts not found" in captured.err


def test_selector_compiler_falls_back_to_canonical_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """When .providence is missing but docs/spec/canonical has mandate docs, they are used."""
    monkeypatch.setattr(canonical_fallback_module, "_BOOTSTRAP_GUIDELINES", None)
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m001.md").write_text(
        """
# Mandate: Clean Architecture

**ID:** M001

**Type:** HARD

**Category:** architecture / design

## Goal

Domain logic must stay isolated from infrastructure details.
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert ids == ["M001"]
    item = payload["items"][0]
    assert item["title"] == "Clean Architecture"
    assert item["category"] == "architecture"
    assert item["mandatory"] is True
    assert (
        item["description"]
        == "Domain logic must stay isolated from infrastructure details."
    )
    captured = capsys.readouterr()
    assert "INFO: .providence artifacts not found" in captured.err


def test_selector_compiler_canonical_doc_without_id_or_title_is_skipped(
    tmp_path: Path,
) -> None:
    """A markdown file missing both ID and title markers is not parsed as a mandate."""
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "not-a-mandate.md").write_text(
        "Just some prose without any mandate markers.\n", encoding="utf-8"
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    assert payload["items"] == []


def test_selector_compiler_canonical_doc_default_category_and_soft_type(
    tmp_path: Path,
) -> None:
    """No Category/Type/Goal sections fall back to defaults; SOFT type maps to mandatory=False."""
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m002.md").write_text(
        """
# Optional Style Guide

**ID:** M002

**Type:** SOFT
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    item = payload["items"][0]
    assert item["id"] == "M002"
    assert item["category"] == "mandate"
    assert item["mandatory"] is False
    assert item["description"] == "Optional Style Guide"


def test_selector_compiler_canonical_docs_skip_duplicate_and_unreadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duplicate IDs across files are deduplicated; unreadable files are skipped."""
    monkeypatch.setattr(canonical_fallback_module, "_BOOTSTRAP_GUIDELINES", None)
    canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "nested"
    canonical_dir.mkdir(parents=True)
    doc = """
# Mandate: Clean Architecture

**ID:** M001

**Type:** HARD
""".strip()
    (canonical_dir / "a.md").write_text(doc, encoding="utf-8")
    (canonical_dir / "b.md").write_text(doc, encoding="utf-8")
    unreadable = canonical_dir / "c.md"
    unreadable.mkdir()

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert ids == ["M001"]


def test_selector_compiler_canonical_goal_skips_non_substantive_paragraphs(
    tmp_path: Path,
) -> None:
    """The Goal extractor skips list/quote/image paragraphs and returns the first prose one."""
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m003.md").write_text(
        """
# Mandate: Testing Discipline

**ID:** M003

**Type:** HARD

## Goal

- a bullet that should be skipped

This is the actual goal paragraph.
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    item = payload["items"][0]
    assert item["description"] == "This is the actual goal paragraph."


def test_selector_compiler_canonical_goal_section_with_only_non_substantive_paragraphs(
    tmp_path: Path,
) -> None:
    """If the Goal section only has skippable paragraphs, description falls back to title."""
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m004.md").write_text(
        """
# Mandate: Empty Goal

**ID:** M004

**Type:** HARD

## Goal

- only a bullet here
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    item = payload["items"][0]
    assert item["description"] == "Empty Goal"


# ---------------------------------------------------------------------------
# Bootstrap guidelines merged into canonical fallback
# ---------------------------------------------------------------------------

_BOOTSTRAP_DSL = """
guideline G01 {
  type: HARD
  title: "Use typed interfaces"
  description: "All public APIs must use typed interfaces."
  category: quality
  tags: ["typing", "api"]
}

guideline G02 {
  title: "No description here"
}
""".strip()


def test_selector_compiler_canonical_fallback_merges_bootstrap_guidelines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When _BOOTSTRAP_GUIDELINES is set, it is parsed and merged into the fallback payload."""
    monkeypatch.setattr(
        canonical_fallback_module, "_BOOTSTRAP_GUIDELINES", _BOOTSTRAP_DSL
    )
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m001.md").write_text(
        """
# Mandate: Clean Architecture

**ID:** M001

**Type:** HARD
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    items_by_id = {item["id"]: item for item in payload["items"]}
    assert set(items_by_id) == {"M001", "G01", "G02"}

    g01 = items_by_id["G01"]
    assert g01["item_type"] == "guideline"
    assert g01["title"] == "Use typed interfaces"
    assert g01["description"] == "All public APIs must use typed interfaces."
    assert g01["category"] == "quality"
    assert g01["mandatory"] is True
    assert g01["tags"] == ["typing", "api"]

    g02 = items_by_id["G02"]
    assert g02["item_type"] == "guideline"
    assert g02["title"] == "No description here"
    assert g02["description"] == "No description here"
    assert g02["category"] == "guideline"
    assert g02["mandatory"] is False
    assert g02["tags"] == ["guideline"]


def test_selector_compiler_bootstrap_guidelines_none_returns_no_guideline_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When _BOOTSTRAP_GUIDELINES is None, the canonical fallback has no guideline items."""
    monkeypatch.setattr(canonical_fallback_module, "_BOOTSTRAP_GUIDELINES", None)
    canonical_dir = tmp_path / "docs" / "spec" / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "m001.md").write_text(
        """
# Mandate: Clean Architecture

**ID:** M001

**Type:** HARD
""".strip(),
        encoding="utf-8",
    )

    compiler = SelectorCompiler(repo_root=tmp_path)
    payload = compiler.build_payload()

    ids = [item["id"] for item in payload["items"]]
    assert ids == ["M001"]


# ---------------------------------------------------------------------------
# Error branches on the primary .providence path
# ---------------------------------------------------------------------------


def test_selector_compiler_missing_section_raises(tmp_path: Path) -> None:
    """A metadata mandate id without a matching '## Mxxx:' section raises ValueError."""
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture", "M002": "Testing"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    compiler = SelectorCompiler(
        repo_root=repo_root, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="Missing selector section for M002"):
        compiler.build_payload()


def test_selector_compiler_metadata_mandates_must_be_mapping(tmp_path: Path) -> None:
    """A non-dict 'mandates' value in metadata.json raises ValueError."""
    (tmp_path / ".providence" / "source" / "mandates").mkdir(parents=True)
    (tmp_path / ".providence" / "metadata.json").write_text(
        json.dumps({"mandates": ["M001"]}), encoding="utf-8"
    )
    (tmp_path / ".providence" / "source" / "mandates" / "mandates.md").write_text(
        "## M001: Clean Architecture\n\nDescription.\n", encoding="utf-8"
    )

    compiler = SelectorCompiler(
        repo_root=tmp_path, asset_source_dir=_write_assets(tmp_path)
    )
    with pytest.raises(ValueError, match="mandates must be a mapping"):
        compiler.build_payload()


# ---------------------------------------------------------------------------
# CLI: _parse_args, main(), and __main__ guard
# ---------------------------------------------------------------------------


def test_parse_args_reads_repo_root_and_output_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["selector_compiler", "--repo-root", "/tmp/repo", "--output-dir", "/tmp/out"],
    )
    args = selector_compiler_cli_module._parse_args()
    assert args.repo_root == "/tmp/repo"
    assert args.output_dir == "/tmp/out"


def test_parse_args_defaults_repo_root_to_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["selector_compiler", "--output-dir", "/tmp/out"])
    args = selector_compiler_cli_module._parse_args()
    assert args.repo_root == "."


def test_main_builds_site_using_parsed_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _write_repo_fixture(
        tmp_path,
        metadata={"mandates": {"M001": "Clean Architecture"}},
        mandates_text="""
## M001: Clean Architecture

Domain logic must stay isolated from infrastructure details.
""".strip(),
    )
    asset_dir = _write_assets(tmp_path)
    output_dir = tmp_path / "site"

    monkeypatch.setattr(
        selector_compiler_module.SelectorCompiler,
        "_asset_dir",
        lambda self: asset_dir,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "selector_compiler",
            "--repo-root",
            str(repo_root),
            "--output-dir",
            str(output_dir),
        ],
    )

    selector_compiler_cli_module.main()

    assert (output_dir / "data.json").exists()


def test_module_main_guard_invokes_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the module as __main__ triggers main() and exits with a usage error."""
    monkeypatch.setattr(sys, "argv", ["selector_compiler_cli"])
    with pytest.raises(SystemExit):
        runpy.run_module(
            "providence_wizard.orchestration.wizard.selector_compiler_cli",
            run_name="__main__",
        )
