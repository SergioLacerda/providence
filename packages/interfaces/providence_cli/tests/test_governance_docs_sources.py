"""Tests for docs-first governance source registry validation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from providence_cli.services.governance_docs_drift import validate_governance_sources
from providence_cli.services.governance_docs_handbook_gen import (
    generate_runtime_handbook,
)
from providence_cli.services.governance_docs_handbook_lookup import (
    lookup_runtime_handbook,
)


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _runtime(root: Path) -> None:
    _write_json(root / ".providence" / "metadata.json", {"mandates": {"M001": "One"}})
    _write_json(
        root / ".providence" / "compiled" / "governance-core.json",
        {"items": [{"id": "M001", "type": "MANDATE"}]},
    )
    _write_json(
        root / ".providence" / "compiled" / "governance-client.json",
        {"items": [{"id": "G01", "type": "GUIDELINE"}]},
    )


def _registry(root: Path, sources: list[dict[str, object]]) -> None:
    path = root / "docs" / "spec" / "canonical" / "governance-sources.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump({"schema_version": "1", "sources": sources}, sort_keys=False),
        encoding="utf-8",
    )


def test_validate_governance_sources_passes_for_matching_runtime(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    (tmp_path / "docs" / "m001.md").parent.mkdir()
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is True
    assert report.mandate_ids == ["M001"]
    assert report.guideline_ids == ["G01"]


def test_validate_governance_sources_detects_duplicate_active_id(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A", encoding="utf-8")
    (docs / "b.md").write_text("# B", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {"id": "M001", "type": "mandate", "status": "active", "path": "docs/a.md"},
            {"id": "M001", "type": "mandate", "status": "active", "path": "docs/b.md"},
            {"id": "G01", "type": "guideline", "status": "active", "path": "docs/a.md"},
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("duplicate active mandate id M001" in error for error in report.errors)


def test_validate_governance_sources_detects_runtime_drift(tmp_path: Path) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    _registry(
        tmp_path,
        [{"id": "M001", "type": "mandate", "status": "active", "path": "docs/m001.md"}],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("guideline registry drift" in error for error in report.errors)


def test_generate_runtime_handbook_writes_index_and_item(tmp_path: Path) -> None:
    _runtime(tmp_path)
    source = tmp_path / "docs" / "cognition" / "context-loading" / "context_flow.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "---",
                "governance_source:",
                "  id: HBK-CONTEXT-LOADING",
                "  title: Context Flow",
                "  summary: Select minimal relevant context.",
                "---",
                "# Context Flow",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "kind": "decision_model",
                "status": "active",
                "path": "docs/cognition/context-loading/context_flow.md",
                "refs": ["M001"],
                "task_types": ["planning"],
                "operation_phases": ["context_loading"],
                "load_policy": {"mode": "selective", "max_tokens": 700},
                "outputs": [
                    ".providence/source/handbook/context-loading/context-flow.yaml"
                ],
            },
        ],
    )

    written = generate_runtime_handbook(tmp_path)

    assert tmp_path / ".providence/source/handbook/index.yaml" in written
    item = yaml.safe_load(
        (
            tmp_path / ".providence/source/handbook/context-loading/context-flow.yaml"
        ).read_text(encoding="utf-8")
    )
    assert item["id"] == "HBK-CONTEXT-LOADING"
    assert item["source_doc"] == "docs/cognition/context-loading/context_flow.md"


def test_generate_runtime_handbook_skips_when_registry_is_absent(
    tmp_path: Path,
) -> None:
    existing = tmp_path / ".providence/source/handbook/index.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("schema_version: '1'\nitems: []\n", encoding="utf-8")

    written = generate_runtime_handbook(tmp_path)

    assert written == []
    assert existing.read_text(encoding="utf-8") == "schema_version: '1'\nitems: []\n"


def test_validate_governance_sources_detects_missing_handbook_output(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    source = tmp_path / "docs" / "cognition" / "context-loading" / "context_flow.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Context Flow", encoding="utf-8")
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "status": "active",
                "path": "docs/cognition/context-loading/context_flow.md",
                "refs": ["M001"],
                "load_policy": {"max_tokens": 700},
                "outputs": [
                    ".providence/source/handbook/context-loading/context-flow.yaml"
                ],
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("handbook runtime output missing" in error for error in report.errors)


def test_validate_governance_sources_detects_handbook_id_collision(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    (docs / "g01.md").write_text("# G01", encoding="utf-8")
    (docs / "hbk.md").write_text("# Handbook", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "M001",
                "type": "handbook",
                "status": "active",
                "path": "docs/hbk.md",
                "task_types": ["planning"],
                "load_policy": {"max_tokens": 700},
            },
        ],
    )

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("handbook id collision" in error for error in report.errors)


def test_lookup_runtime_handbook_matches_generated_index(tmp_path: Path) -> None:
    test_generate_runtime_handbook_writes_index_and_item(tmp_path)

    report = lookup_runtime_handbook(
        tmp_path,
        task_type="planning",
        mandate_refs=["M001"],
        operation_phase="context_loading",
    )

    assert report.status == "matched"
    assert report.diagnostic == "handbook_match=1"
    assert report.matches[0]["id"] == "HBK-CONTEXT-LOADING"


def test_lookup_runtime_handbook_reports_none_without_docs_scan(tmp_path: Path) -> None:
    test_generate_runtime_handbook_writes_index_and_item(tmp_path)

    report = lookup_runtime_handbook(tmp_path, task_type="diagnosis")

    assert report.status == "none"
    assert report.diagnostic == "handbook_match=none"


def test_generate_and_lookup_roundtrip_risk_levels(tmp_path: Path) -> None:
    """CTX-08 regression: the generator used to never write `risk_levels`,
    so `lookup_runtime_handbook`'s `risk_level` filter matched nothing for
    any generated entry, regardless of the registry's declared risk.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` CTX-08.
    """
    _runtime(tmp_path)
    source = tmp_path / "docs" / "cognition" / "context-loading" / "context_flow.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "---",
                "governance_source:",
                "  id: HBK-CONTEXT-LOADING",
                "  title: Context Flow",
                "  summary: Select minimal relevant context.",
                "---",
                "# Context Flow",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "m001.md").write_text("# M001", encoding="utf-8")
    (tmp_path / "docs" / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "kind": "decision_model",
                "status": "active",
                "path": "docs/cognition/context-loading/context_flow.md",
                "refs": ["M001"],
                "task_types": ["planning"],
                "operation_phases": ["context_loading"],
                "risk_levels": ["high"],
                "load_policy": {"mode": "selective", "max_tokens": 700},
                "outputs": [
                    ".providence/source/handbook/context-loading/context-flow.yaml"
                ],
            },
        ],
    )

    generate_runtime_handbook(tmp_path)

    index = yaml.safe_load(
        (tmp_path / ".providence/source/handbook/index.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert index["items"][0]["risk_levels"] == ["high"]

    matching = lookup_runtime_handbook(tmp_path, risk_level="high")
    assert matching.status == "matched"
    assert matching.matches[0]["risk_levels"] == ["high"]

    non_matching = lookup_runtime_handbook(tmp_path, risk_level="low")
    assert non_matching.status == "none"


def test_validate_governance_sources_missing_registry_file(tmp_path: Path) -> None:
    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("missing registry" in error for error in report.errors)
    assert report.mandate_ids == []
    assert report.guideline_ids == []
    assert report.handbook_ids == []


def test_validate_governance_sources_rejects_wrong_schema_version(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)
    path = tmp_path / "docs" / "spec" / "canonical" / "governance-sources.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("schema_version: '2'\nsources: []\n", encoding="utf-8")

    report = validate_governance_sources(tmp_path)

    assert report.ok is False
    assert any("schema_version must be '1'" in error for error in report.errors)


def test_validate_governance_sources_detects_stale_handbook_output(
    tmp_path: Path,
) -> None:
    """A `.providence/source/handbook/` file not declared by any active handbook
    entry (here: no handbook entries at all) must be flagged as stale."""
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    (docs / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
        ],
    )
    stale = tmp_path / ".providence" / "source" / "handbook" / "orphan.yaml"
    stale.parent.mkdir(parents=True)
    stale.write_text("id: ORPHAN\n", encoding="utf-8")

    report = validate_governance_sources(tmp_path)

    assert any(
        "stale handbook runtime output is not declared" in warning
        and "orphan.yaml" in warning
        for warning in report.warnings
    )


def test_validate_governance_sources_detects_readable_source_output_drift(
    tmp_path: Path,
) -> None:
    """`.providence/source/` outputs are checked against every entry's declared
    `outputs`, not just handbook entries  covers both directions: a
    declared-but-missing file and a present-but-undeclared (stale) file."""
    _runtime(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "m001.md").write_text("# M001", encoding="utf-8")
    (docs / "g01.md").write_text("# G01", encoding="utf-8")
    _registry(
        tmp_path,
        [
            {
                "id": "M001",
                "type": "mandate",
                "status": "active",
                "path": "docs/m001.md",
                "outputs": [".providence/source/mandates/mandates.md"],
            },
            {
                "id": "G01",
                "type": "guideline",
                "status": "active",
                "path": "docs/g01.md",
            },
            {
                "id": "HBK-CONTEXT-LOADING",
                "type": "handbook",
                "status": "active",
                "path": "docs/g01.md",
                "task_types": ["planning"],
                "load_policy": {"max_tokens": 700},
            },
        ],
    )
    # Declared (.providence/source/mandates/mandates.md, and the handbook index.yaml
    # implied by the active handbook entry above) are never written to disk;
    # an undeclared stray file is written instead.
    stray = tmp_path / ".providence" / "source" / "stray.txt"
    stray.parent.mkdir(parents=True)
    stray.write_text("unexpected", encoding="utf-8")

    report = validate_governance_sources(tmp_path)

    assert any(
        "declared readable runtime output missing" in warning
        and "mandates.md" in warning
        for warning in report.warnings
    )
    assert any(
        "declared readable runtime output missing" in warning
        and "handbook/index.yaml" in warning
        for warning in report.warnings
    )
    assert any(
        "stale readable runtime output is not declared" in warning
        and "stray.txt" in warning
        for warning in report.warnings
    )
