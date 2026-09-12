from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from providence_integration.assertions.git import GitHasCommitAssertion
from providence_integration.builders.governance.compile import GovernanceCompiler
from providence_integration.runners.command_runner import run_command_exec
from providence_integration.runners.config_runner import run_config_validate
from providence_integration.runners.filesystem_runner import (
    _is_safe_path,
    run_filesystem_copy,
    run_filesystem_create_structure,
)
from providence_integration.runners.git_runner import run_git_commit


def test_run_command_exec_empty_command_noop(tmp_path: Path) -> None:
    ctx = {"working_dir": tmp_path}
    inputs = SimpleNamespace(command="")
    run_command_exec(inputs, ctx, tmp_path)
    assert "last_exit_code" not in ctx


def test_run_command_exec_sets_context_outputs(tmp_path: Path) -> None:
    ctx = {"working_dir": tmp_path}
    inputs = SimpleNamespace(command="echo hello")
    fake_result = SimpleNamespace(returncode=0, stdout="out", stderr="")

    class _Runner:
        def run(self, args: list[str], cwd: Path, timeout: int) -> SimpleNamespace:
            assert args == ["echo", "hello"]
            assert cwd == tmp_path
            assert timeout == 120
            return fake_result

    with patch(
        "providence_core.utils.process.SafeProcessRunner", return_value=_Runner()
    ):
        run_command_exec(inputs, ctx, tmp_path)

    assert ctx["last_exit_code"] == 0
    assert ctx["last_stdout"] == "out"


def test_run_config_validate_defaults_and_parses(tmp_path: Path) -> None:
    ctx = {"working_dir": tmp_path}
    run_config_validate(SimpleNamespace(file=None), ctx, tmp_path)
    assert ctx["config"] == {}

    profile = tmp_path / ".providence" / "profile"
    profile.parent.mkdir(parents=True)
    profile.write_text("[main]\nrepo = yes\n", encoding="utf-8")
    run_config_validate(SimpleNamespace(file=None), ctx, tmp_path)
    assert ctx["config"]["repo"] == "yes"


def test_filesystem_safe_path_and_create_structure(tmp_path: Path) -> None:
    assert _is_safe_path(tmp_path, tmp_path / "a")
    assert not _is_safe_path(tmp_path, tmp_path.parent / "x")
    ctx = {"working_dir": tmp_path}
    run_filesystem_create_structure(
        SimpleNamespace(directories=["a/b", "c"]), ctx, tmp_path
    )
    assert (tmp_path / "a" / "b").exists()
    with pytest.raises(PermissionError):
        run_filesystem_create_structure(
            SimpleNamespace(directories=["../escape"]), ctx, tmp_path
        )


def test_filesystem_copy_file_and_dir_and_block_traversal(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    work = tmp_path / "work"
    spec.mkdir()
    work.mkdir()
    (spec / "f.txt").write_text("x", encoding="utf-8")
    d = spec / "dir1"
    d.mkdir()
    (d / "k.txt").write_text("y", encoding="utf-8")
    ctx = {"working_dir": work}

    run_filesystem_copy(SimpleNamespace(from_="f.txt", to="out/f.txt"), ctx, spec)
    assert (work / "out" / "f.txt").read_text(encoding="utf-8") == "x"
    run_filesystem_copy(SimpleNamespace(from_="dir1", to="dir-copy"), ctx, spec)
    assert (work / "dir-copy" / "k.txt").read_text(encoding="utf-8") == "y"

    with pytest.raises(PermissionError):
        run_filesystem_copy(SimpleNamespace(from_="f.txt", to="../bad"), ctx, spec)


def test_git_runner_init_and_commit_flow(tmp_path: Path) -> None:
    ctx = {"working_dir": tmp_path}
    calls: list[list[str]] = []

    class _Runner:
        def run(self, cmd: list[str], cwd: Path) -> None:
            assert cwd == tmp_path
            calls.append(cmd)

    with patch(
        "providence_core.utils.process.SafeProcessRunner", return_value=_Runner()
    ):
        run_git_commit(SimpleNamespace(message="m1"), ctx, tmp_path)

    assert ["git", "init"] in calls
    assert ["git", "add", "."] in calls
    assert ["git", "commit", "-m", "m1", "--allow-empty"] in calls


def test_git_assertion_success_and_not_found(tmp_path: Path) -> None:
    ok_result = SimpleNamespace(success=True)
    fail_result = SimpleNamespace(success=False)

    class _RunnerOk:
        def run(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
            return ok_result

    class _RunnerFail:
        def run(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
            return fail_result

    assertion = GitHasCommitAssertion()
    with patch(
        "providence_core.utils.process.SafeProcessRunner", return_value=_RunnerOk()
    ):
        assert assertion.execute({"working_dir": tmp_path}).success is True
    with patch(
        "providence_core.utils.process.SafeProcessRunner", return_value=_RunnerFail()
    ):
        assert assertion.execute({"working_dir": tmp_path}).success is False


def test_governance_compiler_end_to_end(tmp_path: Path) -> None:
    core = tmp_path / "core"
    src = core / "source"
    for d in ["mandates", "guidelines", "decisions", "rules", "guardrails"]:
        (src / d).mkdir(parents=True, exist_ok=True)
    (src / "mandates" / "m1.md").write_text(
        "---\nid: M001\ntitle: Mandate\ntype: MANDATE\ncriticality: OBRIGATÓRIO\n---\n",
        encoding="utf-8",
    )
    (src / "guidelines" / "g1.md").write_text(
        "---\nid: G001\ntitle: Guideline\ntype: GUIDELINE\ncustomizable: true\n---\n",
        encoding="utf-8",
    )
    selections = tmp_path / "sel.json"
    selections.write_text(
        json.dumps(
            {"selections": {"M001": {"choice": "CORE"}, "G001": {"choice": "CLIENT"}}}
        ),
        encoding="utf-8",
    )

    c = GovernanceCompiler(str(core))
    c.run(str(selections))

    out = tmp_path / "compiler" / "compiled"
    core_json = json.loads((out / "governance-core.json").read_text(encoding="utf-8"))
    client_json = json.loads(
        (out / "governance-client.json").read_text(encoding="utf-8")
    )
    assert core_json["fingerprint"]
    assert client_json["fingerprint_core_salt"] == core_json["fingerprint"]


def test_governance_compiler_parse_yaml_errors_and_defaults(tmp_path: Path) -> None:
    core = tmp_path / "core"
    src = core / "source" / "mandates"
    src.mkdir(parents=True)
    bad = src / "bad.md"
    bad.write_text("---\n: :\n---", encoding="utf-8")
    c = GovernanceCompiler(str(core))
    c.extract_markdown_items()
    assert c.all_items == []

    # missing selections file should not crash
    c.load_selections(str(tmp_path / "missing.json"))
