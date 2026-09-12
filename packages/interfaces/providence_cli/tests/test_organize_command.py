from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from providence_cli.commands._ask_backend import _should_use_organize, run_sdd_organize
from providence_cli.main import app

runner = CliRunner()


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


def test_organize_output_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".providence" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "providence_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}, {"id": 2}], "retrieval_policy": "indexed_only"},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["organize", "--output-json", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["ok"] is True
    assert payload["data"]["intake_chunks"] == 2
    assert payload["data"]["artifact_path"] == str(artifact_path)


def test_organize_global_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".providence" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "providence_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}], "retrieval_policy": "indexed_only"},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["--json", "organize", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["data"]["intake_chunks"] == 1


def test_organize_json_uses_canonical_data_payload(monkeypatch, tmp_path: Path) -> None:
    artifact_path = tmp_path / ".providence" / "runtime" / "organized.json"
    monkeypatch.setattr(
        "providence_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [{"id": 1}, {"id": 2}, {"id": 3}]},
            artifact_path,
        ),
    )
    result = runner.invoke(app, ["--json", "organize", "hello world"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "organize"
    assert payload["data"]["intake_chunks"] == 3
    assert "intake_chunks" not in payload


def test_organize_accepts_input_file_after_query_argument(
    monkeypatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / ".providence" / "runtime" / "organized.json"
    input_file = tmp_path / "context.txt"
    input_text = "traceback\nerror\nfull file content"
    input_file.write_text(input_text, encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    def _capture_run(**kwargs: object) -> tuple[dict[str, object], Path]:
        captured_kwargs.update(kwargs)
        return (
            {"chunks": [{"id": 1}], "retrieval_policy": "indexed_only"},
            artifact_path,
        )

    monkeypatch.setattr(
        "providence_cli.commands.organize._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.should_use_organize",
        lambda _source_text: (True, "large_input"),
    )
    monkeypatch.setattr(
        "providence_cli.commands.organize.run_sdd_organize", _capture_run
    )

    result = runner.invoke(
        app,
        ["organize", "short query", "--input-file", str(input_file)],
    )

    assert result.exit_code == 0, result.output
    assert captured_kwargs["query"] == "short query"
    assert captured_kwargs["source_text"] == input_text
    assert "artifact_path" in result.output


# ---------------------------------------------------------------------------
# Unmocked behavior of the underlying services.ask_organize functions
# (merged from tests/unit/cli/test_organize_command.py)
# ---------------------------------------------------------------------------


def test_should_use_organize_heavy_by_line_count() -> None:
    payload = "\n".join(f"line {i} error test_case" for i in range(150))
    heavy, reason = _should_use_organize(payload)
    assert heavy is True
    assert reason


def test_should_use_organize_light_for_small_input() -> None:
    heavy, reason = _should_use_organize("small input")
    assert heavy is False
    assert reason == "light_input"


def test_run_sdd_organize_writes_multi_index_artifact(tmp_path: Path) -> None:
    text = "\n".join(
        [
            "test_auth_flow failed",
            "Traceback (most recent call last):",
            "File app/service.py, line 10",
            "ValueError: broken",
        ]
    )
    artifact, path = run_sdd_organize(
        workspace_root=tmp_path,
        query="diagnose auth failures",
        source_text=text,
        route_reason="line_count>=120",
    )
    assert path.exists()
    assert artifact["intake_index_mode"] == "multi"
    assert artifact["retrieval_policy"] == "indexed_only"
    assert "index_by_error_signature" in artifact["indexes"]
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["chunks"]


def test_organize_command_exposed_and_emits_json(monkeypatch, tmp_path: Path) -> None:
    _patch_profile_gate(monkeypatch)
    monkeypatch.setattr(
        "providence_cli.commands.organize._resolve_workspace_root", lambda: tmp_path
    )
    result = CliRunner().invoke(app, ["organize", "sample error"])
    assert result.exit_code == 0, result.output
    assert "sdd-organize completed" in result.output
    artifact_line = next(
        line for line in result.output.splitlines() if line.startswith("artifact_path")
    )
    artifact_path = artifact_line.split(":", 1)[1].strip()
    assert Path(artifact_path).exists()
