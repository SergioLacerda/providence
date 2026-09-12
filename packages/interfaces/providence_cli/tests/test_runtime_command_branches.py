from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from providence_cli.commands import runtime as runtime_cmd


class _FakeAHP:
    skill_profile = "client"

    def format_combined_output(self, state: str, report, mode: str) -> str:  # noqa: ANN001
        return f"{state}:{mode}"


def test_render_status_output_json_error_path(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "providence_cli.shared.contracts.build_error_result",
        lambda command, data, code, message: {
            "status": "error",
            "data": data,
            "error": {"code": code, "message": message},
        },
    )
    monkeypatch.setattr(
        runtime_cmd, "emit_json", lambda payload, err=False: print(json.dumps(payload))
    )
    runtime_cmd._render_status_output(
        ahp=_FakeAHP(),
        state="MISCONFIGURED",
        report=SimpleNamespace(status="bad"),
        code=2,
        drift_info={"detected": True, "type": "spec_drift"},
        governance_footer="FOOTER",
        cache_staleness={"stale": True, "age_min": 20, "missing": False},
        ask_confidence=None,
        output_json=True,
        output_mode="compact",
    )
    out = capsys.readouterr().out
    assert "runtime_state_not_healthy" in out


def test_render_status_output_text_stale_warning(capsys) -> None:
    runtime_cmd._render_status_output(
        ahp=_FakeAHP(),
        state="HEALTHY",
        report=SimpleNamespace(status="ok"),
        code=0,
        drift_info={"detected": False, "type": "none"},
        governance_footer="FOOTER",
        cache_staleness={"stale": True, "age_min": 20, "missing": False},
        ask_confidence=None,
        output_json=False,
        output_mode="compact",
    )
    out = capsys.readouterr().out
    assert "WARNING L2" in out
    assert "FOOTER" in out


def test_do_update_cache_writes_new_cache(monkeypatch, tmp_path: Path, capsys) -> None:
    gov = tmp_path / ".providence" / "compiled" / "governance-core.json"
    gov.parent.mkdir(parents=True)
    gov.write_text("{}", encoding="utf-8")

    class _FakeAst:
        enforcement_steps = ["step 1", "step 2"]

    fake_module = SimpleNamespace(
        GovernanceAST=SimpleNamespace(
            from_compiled_json=lambda path: SimpleNamespace(
                item_by_id=lambda item_id: _FakeAst()
            )
        )
    )
    monkeypatch.setitem(
        __import__("sys").modules, "providence_core.governance.ast", fake_module
    )
    runtime_cmd._do_update_cache(tmp_path)
    out = capsys.readouterr().out
    cache = tmp_path / ".providence" / "runtime" / ".providence-cache.md"
    assert ".providence-cache.md refreshed" in out
    assert cache.exists()
    assert "Validation Quiz" in cache.read_text(encoding="utf-8")


def test_do_update_cache_appends_validation_quiz_to_existing_cache(
    monkeypatch, tmp_path: Path
) -> None:
    gov = tmp_path / ".providence" / "compiled" / "governance-core.json"
    gov.parent.mkdir(parents=True)
    gov.write_text("{}", encoding="utf-8")
    cache = tmp_path / ".providence" / "runtime" / ".providence-cache.md"
    cache.parent.mkdir(parents=True)
    cache.write_text("# SDD Cache\n\nInitialized by: previous run\n", encoding="utf-8")

    class _FakeAst:
        enforcement_steps = ["step 1", "step 2"]

    fake_module = SimpleNamespace(
        GovernanceAST=SimpleNamespace(
            from_compiled_json=lambda path: SimpleNamespace(
                item_by_id=lambda item_id: _FakeAst()
            )
        )
    )
    monkeypatch.setitem(
        __import__("sys").modules, "providence_core.governance.ast", fake_module
    )

    runtime_cmd._do_update_cache(tmp_path)

    text = cache.read_text(encoding="utf-8")
    assert "Initialized by: previous run" in text
    assert "Validation Quiz" in text


def test_do_update_cache_missing_governance_file_raises(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit) as exc:
        runtime_cmd._do_update_cache(tmp_path)
    assert exc.value.exit_code == 1


def test_format_diagnostic_block_handles_missing_and_unreadable_cache(
    monkeypatch, tmp_path: Path
) -> None:
    profile = tmp_path / ".providence" / "profile"
    profile.parent.mkdir(parents=True)
    profile.write_text("[sdd]\ntype = client\n", encoding="utf-8")
    monkeypatch.setattr(runtime_cmd, "profile_active_path", lambda root: profile)
    monkeypatch.setattr(runtime_cmd, "_read_profile", lambda root: "client")
    block = runtime_cmd._format_diagnostic_block(
        tmp_path, cache_file=tmp_path / "missing.json"
    )
    assert "NONE, revalidating" in block

    cache = tmp_path / ".providence" / "runtime" / "governance-state.json"
    cache.parent.mkdir(parents=True)
    cache.write_text("not-json", encoding="utf-8")
    block = runtime_cmd._format_diagnostic_block(tmp_path, cache_file=cache)
    assert "unreadable" in block
