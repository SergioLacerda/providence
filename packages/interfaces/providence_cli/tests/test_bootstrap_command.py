"""Unit tests for `sdd bootstrap run` command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from providence_cli.commands.bootstrap import run

pytestmark = pytest.mark.unit


def _write_workspace_files(
    root: Path,
    fingerprint: str = "fp-123",
    version: str = "3.0",
    mandates_count: int = 8,
) -> None:
    (root / ".providence" / "source").mkdir(parents=True, exist_ok=True)
    (root / ".providence" / "metadata.json").write_text(
        json.dumps(
            {
                "spec_fingerprint": fingerprint,
                "version": version,
                "mandates_count": mandates_count,
            }
        ),
        encoding="utf-8",
    )
    (root / ".providence" / "source" / "governance-core.json").write_text(
        json.dumps({"items": []}), encoding="utf-8"
    )


class TestBootstrapCommand:
    def test_run_writes_bootstrap_state(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        _write_workspace_files(tmp_path)
        monkeypatch.chdir(tmp_path)
        run(session_guard_hours=4)
        out = capsys.readouterr().out

        state_path = tmp_path / ".providence" / "runtime" / "bootstrap-state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["governance_fingerprint"] == "fp-123"
        assert data["session_guard_hours"] == 4
        assert "version=3.0" in out
        assert "mandates=8" in out
        assert "fingerprint=fp-123" in out

    def test_run_exits_when_required_files_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(typer.Exit) as exc_info:
            run(session_guard_hours=4)
        assert exc_info.value.exit_code == 1

    def test_run_respects_guard_for_same_fingerprint(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        _write_workspace_files(tmp_path)
        monkeypatch.chdir(tmp_path)
        run(session_guard_hours=4)
        first = json.loads(
            (tmp_path / ".providence" / "runtime" / "bootstrap-state.json").read_text(
                encoding="utf-8"
            )
        )
        run(session_guard_hours=4)
        second = json.loads(
            (tmp_path / ".providence" / "runtime" / "bootstrap-state.json").read_text(
                encoding="utf-8"
            )
        )
        output = capsys.readouterr().out
        assert "up-to-date" in output
        assert "version=3.0" in output
        assert "mandates=8" in output
        assert first["last_success_at"] == second["last_success_at"]

    def test_run_exits_2_when_providence_core_not_installed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        _write_workspace_files(tmp_path)
        monkeypatch.chdir(tmp_path)
        import builtins

        real_import = builtins.__import__

        def _block_providence_core(name, *args, **kwargs):
            if name == "providence_core.utils.environment":
                raise ImportError("providence_core not available")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_providence_core)
        with pytest.raises(typer.Exit) as exc_info:
            run(session_guard_hours=4)
        assert exc_info.value.exit_code == 2

    def test_run_falls_back_to_governance_items_when_mandates_count_missing(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        (tmp_path / ".providence" / "source").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".providence" / "metadata.json").write_text(
            json.dumps({"spec_fingerprint": "fp-fallback", "version": "3.1"}),
            encoding="utf-8",
        )
        (tmp_path / ".providence" / "source" / "governance-core.json").write_text(
            json.dumps({"items": [{}, {}, {}]}), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        run(session_guard_hours=4)
        out = capsys.readouterr().out
        assert "mandates=3" in out


class TestReadJson:
    def test_returns_empty_dict_on_invalid_json(self, tmp_path: Path) -> None:
        from providence_cli.commands.bootstrap import _read_json

        bad = tmp_path / "bad.json"
        bad.write_text("not-json", encoding="utf-8")
        assert _read_json(bad) == {}

    def test_returns_empty_dict_on_non_dict_json(self, tmp_path: Path) -> None:
        from providence_cli.commands.bootstrap import _read_json

        bad = tmp_path / "list.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")
        assert _read_json(bad) == {}

    def test_returns_empty_dict_on_missing_file(self, tmp_path: Path) -> None:
        from providence_cli.commands.bootstrap import _read_json

        assert _read_json(tmp_path / "nonexistent.json") == {}


class TestParseIso:
    def test_returns_none_for_empty_string(self) -> None:
        from providence_cli.commands.bootstrap import _parse_iso

        assert _parse_iso("") is None
        assert _parse_iso(None) is None

    def test_returns_none_for_invalid_iso(self) -> None:
        from providence_cli.commands.bootstrap import _parse_iso

        assert _parse_iso("not-a-date") is None

    def test_normalizes_z_suffix(self) -> None:
        from providence_cli.commands.bootstrap import _parse_iso

        result = _parse_iso("2026-01-15T10:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_adds_utc_to_naive_datetime(self) -> None:
        from providence_cli.commands.bootstrap import _parse_iso

        result = _parse_iso("2026-01-15T10:00:00")
        assert result is not None
        from datetime import timezone

        assert result.tzinfo == timezone.utc
