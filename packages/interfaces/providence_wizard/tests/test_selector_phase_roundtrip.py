"""Roundtrip tests: selector-selection.json  Phase 1 filter.

Verifies that IDs emitted by the selector (M-IDs and G-IDs) are correctly
applied by Phase1Generator._apply_selector_selection() so only selected items
survive into the generated output.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.orchestration.wizard.models import Guideline, Mandate
from providence_wizard.orchestration.wizard.phase1_generator import Phase1Generator


def _make_generator(
    tmp_path: Path,
    *,
    selector_resolved_ids: list[str] | None = None,
) -> Phase1Generator:
    core_path = tmp_path / "core"
    output_path = tmp_path / "output"
    core_path.mkdir(parents=True)
    output_path.mkdir(parents=True)
    config: dict[str, object] = {}
    if selector_resolved_ids is not None:
        config["selector_selection"] = {
            "version": "1.0",
            "selected_ids": selector_resolved_ids,
            "resolved_ids": selector_resolved_ids,
        }
    with patch(
        "providence_wizard.orchestration.wizard.phase1_generator.get_sdd_paths"
    ) as mock_paths:
        mock_paths.side_effect = RuntimeError("no sdd paths in test")
        gen = Phase1Generator(
            core_path=core_path,
            output_path=output_path,
            config=config,
            emitter=lambda _: None,
        )
    return gen


def _seed_items(gen: Phase1Generator) -> None:
    gen.mandates = [
        Mandate(
            id="M001",
            type="HARD",
            title="Clean Arch",
            description="Desc",
            category="arch",
            rationale="",
        ),
        Mandate(
            id="M002",
            type="HARD",
            title="Testing",
            description="Desc",
            category="quality",
            rationale="",
        ),
        Mandate(
            id="M003",
            type="SOFT",
            title="Docs",
            description="Desc",
            category="docs",
            rationale="",
        ),
    ]
    gen.guidelines = [
        Guideline(
            id="G01",
            type="HARD",
            title="Typed APIs",
            description="Desc",
            category="quality",
        ),
        Guideline(
            id="G02",
            type="SOFT",
            title="Immutable data",
            description="Desc",
            category="style",
        ),
    ]


class TestSelectorMandateFilter:
    def test_no_selector_keeps_all_mandates(self, tmp_path: Path) -> None:
        gen = _make_generator(tmp_path)
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert [m.id for m in gen.mandates] == ["M001", "M002", "M003"]

    def test_selector_with_mandate_ids_filters_mandates(self, tmp_path: Path) -> None:
        gen = _make_generator(tmp_path, selector_resolved_ids=["M001", "M003"])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert [m.id for m in gen.mandates] == ["M001", "M003"]
        assert [g.id for g in gen.guidelines] == []

    def test_selector_empty_list_is_treated_as_no_filter(self, tmp_path: Path) -> None:
        # Empty resolved_ids is falsy; Phase1Generator treats it as "no selector active"
        # and keeps all items unchanged. This matches the existing contract.
        gen = _make_generator(tmp_path, selector_resolved_ids=[])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert len(gen.mandates) == 3
        assert len(gen.guidelines) == 2


class TestSelectorGuidelineFilter:
    def test_selector_with_guideline_ids_filters_guidelines(
        self, tmp_path: Path
    ) -> None:
        gen = _make_generator(tmp_path, selector_resolved_ids=["M001", "G01"])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert [m.id for m in gen.mandates] == ["M001"]
        assert [g.id for g in gen.guidelines] == ["G01"]

    def test_selector_guideline_only_keeps_no_mandates(self, tmp_path: Path) -> None:
        gen = _make_generator(tmp_path, selector_resolved_ids=["G02"])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert gen.mandates == []
        assert [g.id for g in gen.guidelines] == ["G02"]

    def test_selector_all_ids_keeps_all_items(self, tmp_path: Path) -> None:
        gen = _make_generator(
            tmp_path, selector_resolved_ids=["M001", "M002", "M003", "G01", "G02"]
        )
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is True
        assert len(gen.mandates) == 3
        assert len(gen.guidelines) == 2


class TestSelectorUnknownIds:
    def test_unknown_id_returns_false_and_sets_error(self, tmp_path: Path) -> None:
        gen = _make_generator(tmp_path, selector_resolved_ids=["M001", "M999"])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is False
        assert gen.last_error is not None
        assert "M999" in gen.last_error

    def test_unknown_guideline_id_returns_false(self, tmp_path: Path) -> None:
        gen = _make_generator(tmp_path, selector_resolved_ids=["G99"])
        _seed_items(gen)
        result = gen._apply_selector_selection()
        assert result is False
        assert gen.last_error is not None
        assert "G99" in gen.last_error
