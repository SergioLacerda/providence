"""Tests for GovernanceLoader and SeedlingsOrchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_wizard.orchestration.phase4_governance_loader import GovernanceLoader
from providence_wizard.orchestration.phase6_seedlings_orchestrator import (
    SeedlingsOrchestrator,
)

# ---------------------------------------------------------------------------
# GovernanceLoader tests
# ---------------------------------------------------------------------------


def _write_core(path: Path, items: list[dict] | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "items": items
                or [
                    {"id": "M001", "type": "MANDATE", "title": "Dep gov"},
                    {
                        "id": "G01",
                        "type": "GUIDELINE",
                        "title": "Commits",
                        "category": "git",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


class TestGovernanceLoader:
    def test_load_returns_true_with_valid_files(self, tmp_path: Path) -> None:
        core = tmp_path / "governance-core.json"
        client = tmp_path / "governance-client.json"
        _write_core(core)
        _write_core(
            client,
            items=[
                {"id": "G02", "type": "GUIDELINE", "title": "Style", "category": "code"}
            ],
        )
        loader = GovernanceLoader(core, client, verbose=False)
        assert loader.load() is True
        assert len(loader.mandates) == 1
        assert "G01" in loader.guidelines

    def test_load_returns_false_when_core_missing(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(
            tmp_path / "missing.json", tmp_path / "missing-client.json"
        )
        assert loader.load() is False

    def test_load_skips_client_when_missing(self, tmp_path: Path) -> None:
        core = tmp_path / "governance-core.json"
        _write_core(core)
        loader = GovernanceLoader(core, tmp_path / "nonexistent-client.json")
        assert loader.load() is True

    def test_load_returns_false_on_json_error(self, tmp_path: Path) -> None:
        core = tmp_path / "governance-core.json"
        core.write_text("{ invalid json", encoding="utf-8")
        loader = GovernanceLoader(core, tmp_path / "c.json")
        assert loader.load() is False

    def test_normalize_type_from_id_prefix(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(tmp_path / "a.json", tmp_path / "b.json")
        assert loader._normalize_item_type({"id": "M001"}) == "MANDATE"
        assert loader._normalize_item_type({"id": "G01"}) == "GUIDELINE"
        assert loader._normalize_item_type({"id": "X99"}) == ""

    def test_normalize_type_from_type_field(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(tmp_path / "a.json", tmp_path / "b.json")
        assert loader._normalize_item_type({"type": "mandate"}) == "MANDATE"
        assert loader._normalize_item_type({"type": "GUIDELINE"}) == "GUIDELINE"

    def test_normalize_type_uses_default_when_unknown(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(tmp_path / "a.json", tmp_path / "b.json")
        assert loader._normalize_item_type({"type": "unknown"}, "MANDATE") == "MANDATE"

    def test_ingest_deduplicates_mandates(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(tmp_path / "a.json", tmp_path / "b.json")
        items = [{"id": "M001", "type": "MANDATE"}, {"id": "M001", "type": "MANDATE"}]
        loader._ingest_items(items, set())
        assert len(loader.mandates) == 1

    def test_ingest_skips_items_without_id(self, tmp_path: Path) -> None:
        loader = GovernanceLoader(tmp_path / "a.json", tmp_path / "b.json")
        loader._ingest_items([{"type": "MANDATE"}], set())
        assert len(loader.mandates) == 0

    def test_guidelines_grouped_by_category(self, tmp_path: Path) -> None:
        core = tmp_path / "governance-core.json"
        _write_core(
            core,
            items=[
                {"id": "G01", "type": "GUIDELINE", "title": "A", "category": "git"},
                {"id": "G02", "type": "GUIDELINE", "title": "B", "category": "git"},
                {"id": "G03", "type": "GUIDELINE", "title": "C", "category": "testing"},
            ],
        )
        loader = GovernanceLoader(core, tmp_path / "c.json")
        loader.load()
        assert len(loader.guidelines_by_category["git"]) == 2
        assert len(loader.guidelines_by_category["testing"]) == 1

    def test_verbose_mode_prints(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        core = tmp_path / "governance-core.json"
        _write_core(core)
        loader = GovernanceLoader(core, tmp_path / "c.json", verbose=True)
        loader.load()
        captured = capsys.readouterr()
        assert "Loading" in captured.out


# ---------------------------------------------------------------------------
# SeedlingsOrchestrator tests
# ---------------------------------------------------------------------------


def _make_orchestrator(tmp_path: Path) -> SeedlingsOrchestrator:
    return SeedlingsOrchestrator(
        output_base=tmp_path,
        mandates=[{"id": "M001", "title": "T"}],
        guidelines_by_category={"git": [{"id": "G01", "title": "Commits"}]},
        config={"language": "Python"},
        governance_core_path=tmp_path / "governance-core.json",
        paths={"client_compiled": tmp_path, "master_compiled": tmp_path},
        verbose=False,
    )


class TestSeedlingsOrchestrator:
    def test_generate_returns_true_on_success(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        mock_gen = MagicMock()
        mock_gen.generate_all.return_value = True
        mock_gen.get_summary.return_value = {
            "count": 5,
            "fingerprint": "abc",
            "mandates": ["M001"],
            "guidelines": ["git"],
        }
        with patch(
            "providence_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator",
            return_value=mock_gen,
        ):
            assert orch.generate() is True

    def test_generate_returns_false_on_generator_failure(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        mock_gen = MagicMock()
        mock_gen.generate_all.return_value = False
        with patch(
            "providence_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator",
            return_value=mock_gen,
        ):
            assert orch.generate() is False

    def test_generate_returns_false_on_exception(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "providence_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator",
            side_effect=RuntimeError("unexpected"),
        ):
            assert orch.generate() is False

    def test_generate_passes_selected_codex_to_generator(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        mock_gen = MagicMock()
        mock_gen.generate_all.return_value = True
        mock_gen.get_summary.return_value = {
            "count": 1,
            "fingerprint": "abc",
            "mandates": ["M001"],
            "guidelines": ["git"],
        }
        with patch(
            "providence_wizard.orchestration.phase6_seedlings_orchestrator.IntelligentSeedlingsGenerator",
            return_value=mock_gen,
        ):
            assert orch.generate(selected={"codex"}) is True
        mock_gen.generate_all.assert_called_once_with(selected={"codex"})

    def test_resolve_governance_path_returns_existing(self, tmp_path: Path) -> None:
        core = tmp_path / "governance-core.json"
        core.write_text("{}", encoding="utf-8")
        orch = _make_orchestrator(tmp_path)
        orch.governance_core_path = core
        result = orch._resolve_governance_path()
        assert result == core

    def test_resolve_governance_path_fallback_when_none_exist(
        self, tmp_path: Path
    ) -> None:
        orch = _make_orchestrator(tmp_path)
        # governance_core_path doesn't exist  returns it as fallback
        result = orch._resolve_governance_path()
        assert result == orch.governance_core_path
