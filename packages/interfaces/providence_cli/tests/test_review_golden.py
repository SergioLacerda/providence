"""Tests for providence test review-golden CLI command (Phase 2 4).

Covers:
- First run: initialises golden snapshot and exits 0
- Clean run: no changes, exits 0
- Non-breaking changes: exits 0 by default
- Breaking changes: exits 1 when --fail-on-breaking (default)
- Breaking changes: exits 0 when --no-fail-on-breaking
- --update: refreshes golden and exits 0
- Missing artifact: exits 1 with Next: hint
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from tests.helpers.text_io import read_text_utf8
from typer.testing import CliRunner

from providence_cli.commands.test import app as test_app


def _make_ast_dict(items: list[dict], fingerprint: str = "fp-test") -> dict:
    return {
        "ast_version": "1.0",
        "source_fingerprint": fingerprint,
        "generated_at": "2026-05-10T00:00:00+00:00",
        "profile": "master",
        "items": items,
    }


def _item(id: str, title: str, item_type: str = "MANDATE") -> dict:
    return {"id": id, "title": title, "item_type": item_type, "description": ""}


def _artifact_json(items: list[dict]) -> dict:
    return {
        "category": "CORE",
        "version": "3.0",
        "fingerprint": "fp-artifact",
        "items": items,
    }


def _write_artifact(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_artifact_json(items)), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(
    tmp_path: Path, extra_args: list[str], artifact_items: list[dict] | None = None
):
    runner = CliRunner()
    artifact_path = tmp_path / ".providence" / "compiled" / "governance-core.json"
    golden_path = tmp_path / ".providence" / "runtime" / "golden-ast.json"

    if artifact_items is not None:
        _write_artifact(artifact_path, artifact_items)

    with patch("providence_cli.commands.test.detect_repo_root", return_value=tmp_path):
        result = runner.invoke(test_app, ["review-golden"] + extra_args)
    return result, artifact_path, golden_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReviewGoldenFirstRun:
    def test_initialises_golden_on_first_run(self, tmp_path: Path) -> None:
        result, _, golden_path = _invoke(
            tmp_path, [], artifact_items=[_item("M001", "Clean Arch")]
        )
        assert result.exit_code == 0
        assert golden_path.exists()
        data = json.loads(read_text_utf8(golden_path))
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "M001"

    def test_first_run_prints_initialised_message(self, tmp_path: Path) -> None:
        result, _, _ = _invoke(tmp_path, [], artifact_items=[_item("M001", "A")])
        assert (
            "initialised" in result.output.lower()
            or "initialized" in result.output.lower()
        )


class TestReviewGoldenClean:
    def test_clean_exits_0(self, tmp_path: Path) -> None:
        items = [_item("M001", "Clean Arch")]
        # First run: initialise
        _invoke(tmp_path, [], artifact_items=items)
        # Second run: same artifact  clean
        result, _, _ = _invoke(tmp_path, [], artifact_items=items)
        assert result.exit_code == 0
        assert "CLEAN" in result.output or "No changes" in result.output


class TestReviewGoldenBreaking:
    def test_breaking_change_exits_1_by_default(self, tmp_path: Path) -> None:
        # Initialise with M001 + M002
        _invoke(tmp_path, [], artifact_items=[_item("M001", "A"), _item("M002", "B")])
        # Run with M002 removed (breaking)
        result, _, _ = _invoke(tmp_path, [], artifact_items=[_item("M001", "A")])
        assert result.exit_code == 1
        assert "Next:" in result.output or "breaking" in result.output.lower()

    def test_breaking_change_no_fail_exits_0(self, tmp_path: Path) -> None:
        _invoke(tmp_path, [], artifact_items=[_item("M001", "A"), _item("M002", "B")])
        result, _, _ = _invoke(
            tmp_path, ["--no-fail-on-breaking"], artifact_items=[_item("M001", "A")]
        )
        assert result.exit_code == 0


class TestReviewGoldenNonBreaking:
    def test_non_breaking_change_exits_0(self, tmp_path: Path) -> None:
        _invoke(tmp_path, [], artifact_items=[_item("M001", "Old Title")])
        result, _, _ = _invoke(
            tmp_path, [], artifact_items=[_item("M001", "New Title")]
        )
        assert result.exit_code == 0
        assert (
            "non-breaking" in result.output.lower() or "Non-breaking" in result.output
        )


class TestReviewGoldenUpdate:
    def test_update_refreshes_golden(self, tmp_path: Path) -> None:
        _invoke(tmp_path, [], artifact_items=[_item("M001", "Old")])
        result, _, golden_path = _invoke(
            tmp_path,
            ["--update"],
            artifact_items=[_item("M001", "New"), _item("M002", "Added")],
        )
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
        data = json.loads(read_text_utf8(golden_path))
        assert len(data["items"]) == 2


class TestReviewGoldenMissingArtifact:
    def test_missing_artifact_exits_1(self, tmp_path: Path) -> None:
        # No artifact written
        result, _, _ = _invoke(tmp_path, [], artifact_items=None)
        assert result.exit_code == 1
        assert "Next:" in result.output
