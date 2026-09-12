from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from providence_cli.services import test_handler as handler


def test_check_import_false_for_missing_module() -> None:
    assert handler._check_import("module_that_does_not_exist_123") is False


def test_run_helpers_pass_expected_commands(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class _Runner:
        def run(self, args, cwd=None, env=None):  # noqa: ANN001
            calls.append(args)
            assert env["PYTHONUTF8"] == "1"
            return SimpleNamespace(returncode=7)

    monkeypatch.setattr(
        "providence_core.utils.process.SafeProcessRunner", lambda: _Runner()
    )
    assert handler._run_script("script.py", ["--verbose"], str(tmp_path)) == 7
    assert handler._run_cli(["runtime", "status"], str(tmp_path)) == 7
    assert handler._run_pytest(["-q"], str(tmp_path)) == 7
    assert calls[0][1] == "script.py"
    assert calls[1][1:3] == ["-m", "providence_cli"]
    assert calls[2][1:3] == ["-m", "pytest"]


def test_find_artifact_and_save_golden(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / ".providence" / "compiled" / "governance-core.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")
    assert handler._find_artifact(tmp_path) == artifact

    golden = tmp_path / ".providence" / "runtime" / "golden-ast.json"
    fake_ast = SimpleNamespace(
        to_json=lambda: '{"items": []}',
        items=[],
        source_fingerprint="abcdef012345",
    )
    handler._save_golden(golden, fake_ast)
    assert golden.exists()
    assert "Golden snapshot updated" in capsys.readouterr().out


def test_load_golden_ast_invalid_json_raises_exit(tmp_path: Path) -> None:
    golden = tmp_path / "golden.json"
    golden.write_text("{bad", encoding="utf-8")
    with pytest.raises(typer.Exit):
        handler._load_golden_ast(golden)
