"""Regression tests for top-level ask entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from click.testing import CliRunner

from providence_cli.main import app


@dataclass
class _FakeProfileContext:
    def as_dict(self) -> dict[str, object]:
        return {"profile": "client", "is_master": False, "is_client": True}


def _patch_profile_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_core.utils.environment.resolve_profile",
        lambda override=None: _FakeProfileContext(),
    )
    monkeypatch.setattr(
        "providence_cli.utils.profile.governance_gate", lambda _ctx: None
    )


def test_ask_top_level_invocation_without_duplication(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called: dict[str, object] = {}

    def _fake_ask_cmd(
        query: str,
        dossier: bool = False,
        skill: str | None = None,
        budget: int | None = None,
        full: bool = False,
        log_path: str | None = None,
        log_format: str = "jsonl",
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        intake_only: bool = False,
        output_json: bool | None = None,
    ) -> None:
        called["query"] = query
        called["dossier"] = dossier
        called["skill"] = skill
        called["budget"] = budget
        called["full"] = full
        called["intake_only"] = intake_only
        called["output_json"] = output_json

    monkeypatch.setattr("providence_cli.commands._ask_backend.ask_cmd", _fake_ask_cmd)

    result = CliRunner().invoke(app, ["ask", "prompt"])
    assert result.exit_code == 0, result.output
    assert called["query"] == "prompt"
    assert called["output_json"] is False
    assert called["full"] is False


def test_ask_top_level_noop_when_query_is_empty_or_null(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called = {"count": 0}

    def _fake_ask_cmd(
        query: str,
        dossier: bool = False,
        skill: str | None = None,
        budget: int | None = None,
        full: bool = False,
        log_path: str | None = None,
        log_format: str = "jsonl",
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        intake_only: bool = False,
        output_json: bool | None = None,
    ) -> None:
        called["count"] += 1

    monkeypatch.setattr("providence_cli.commands._ask_backend.ask_cmd", _fake_ask_cmd)
    runner = CliRunner()

    for raw_query in ("", "   ", "null", "NULL", "nula", "NULA"):
        result = runner.invoke(app, ["ask", raw_query])
        assert result.exit_code == 0, result.output

    assert called["count"] == 0


def test_ask_full_flag_passes_full_true_to_ask_cmd(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    called: dict[str, object] = {}

    def _fake_ask_cmd(
        query: str,
        dossier: bool = False,
        skill: str | None = None,
        budget: int | None = None,
        full: bool = False,
        log_path: str | None = None,
        log_format: str = "jsonl",
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        intake_only: bool = False,
        output_json: bool | None = None,
    ) -> None:
        called["query"] = query
        called["full"] = full
        called["log_format"] = log_format
        called["tokens_input"] = tokens_input
        called["tokens_output"] = tokens_output
        called["intake_only"] = intake_only
        called["output_json"] = output_json

    monkeypatch.setattr("providence_cli.commands._ask_backend.ask_cmd", _fake_ask_cmd)

    result = CliRunner().invoke(app, ["ask", "--full", "prompt"])
    assert result.exit_code == 0, result.output
    assert called["query"] == "prompt"
    assert called["full"] is True


def test_ask_full_flag_help_shows_canonical_usage(monkeypatch) -> None:
    _patch_profile_gate(monkeypatch)
    ask_command = app.get_command(None, "ask")
    option_names = {opt for param in ask_command.params for opt in param.opts}
    assert "--full" in option_names

    result = CliRunner().invoke(app, ["ask", "--help"])
    assert result.exit_code == 0, result.output
    assert "ask ask" not in result.output
