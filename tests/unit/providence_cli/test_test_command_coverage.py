"""Coverage tests for providence_cli.commands.test."""

from __future__ import annotations

import builtins
import sys
import types
from pathlib import Path

import pytest
import typer

from providence_cli.commands import test as test_mod
from providence_cli.services.test_handler import (
    _find_artifact,
    _resolve_golden_path,
    _save_golden,
)


class _Runner:
    def __init__(self, behavior: object = 0) -> None:
        self.behavior = behavior
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def run(self, cmd: list[str], **kwargs: object) -> object:
        self.calls.append((cmd, kwargs))
        if isinstance(self.behavior, Exception):
            raise self.behavior
        if isinstance(self.behavior, int):
            return types.SimpleNamespace(returncode=self.behavior)
        return self.behavior


def _install_process_runner(
    monkeypatch: pytest.MonkeyPatch, behavior: object = 0
) -> _Runner:
    runner = _Runner(behavior)
    from providence_core.utils._process_types import ProcessResult

    process_mod = types.ModuleType("providence_core.utils.process")
    process_mod.ProcessAuthorizationError = type(
        "ProcessAuthorizationError", (Exception,), {}
    )
    process_mod.ProcessNonZeroExitError = type(
        "ProcessNonZeroExitError", (Exception,), {}
    )
    process_mod.ProcessSpawnError = type("ProcessSpawnError", (Exception,), {})
    process_mod.ProcessTimeoutError = type("ProcessTimeoutError", (Exception,), {})
    process_mod.ProcessResult = ProcessResult
    process_mod.SafeProcessRunner = lambda: runner
    monkeypatch.setitem(sys.modules, "providence_core.utils.process", process_mod)
    return runner


def _install_golden_ast(
    monkeypatch: pytest.MonkeyPatch,
    *,
    current_ast: object,
    golden_ast: object,
) -> None:
    ast_mod = types.ModuleType("providence_core.governance.ast")

    class _GovernanceAST:
        @classmethod
        def from_compiled_json(cls, path: Path):
            return current_ast

        @classmethod
        def from_dict(cls, raw: dict[str, object]):
            return golden_ast

    ast_mod.GovernanceAST = _GovernanceAST
    monkeypatch.setitem(sys.modules, "providence_core.governance.ast", ast_mod)


class TestRunCommand:
    def test_run_success_and_flags(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        script = root / "tools" / "testing" / "run-all-tests.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("", encoding="utf-8")
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        runner = _install_process_runner(monkeypatch, 0)
        test_mod.TestCommand().run(True, True, False, 90)
        cmd = runner.calls[0][0]
        assert "--verbose" in cmd
        assert "--fail-fast" in cmd
        assert "--no-coverage" in cmd

    def test_run_error_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        script = root / "tools" / "testing" / "run-all-tests.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("", encoding="utf-8")
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)

        errors = [
            (test_mod, "ProcessNonZeroExitError", 1),
            (test_mod, "ProcessAuthorizationError", 2),
            (test_mod, "ProcessTimeoutError", 124),
            (test_mod, "ProcessSpawnError", 127),
        ]
        for _name_module, exc_name, code in errors:
            from providence_core.utils._process_types import ProcessResult

            process_mod = types.ModuleType("providence_core.utils.process")
            process_mod.ProcessAuthorizationError = type(
                "ProcessAuthorizationError", (Exception,), {}
            )
            process_mod.ProcessNonZeroExitError = type(
                "ProcessNonZeroExitError", (Exception,), {}
            )
            process_mod.ProcessSpawnError = type("ProcessSpawnError", (Exception,), {})
            process_mod.ProcessTimeoutError = type(
                "ProcessTimeoutError", (Exception,), {}
            )
            process_mod.ProcessResult = ProcessResult
            error_map = {
                "ProcessNonZeroExitError": process_mod.ProcessNonZeroExitError("boom"),
                "ProcessAuthorizationError": process_mod.ProcessAuthorizationError(
                    "boom"
                ),
                "ProcessTimeoutError": process_mod.ProcessTimeoutError("boom"),
                "ProcessSpawnError": process_mod.ProcessSpawnError("boom"),
            }
            process_mod.SafeProcessRunner = lambda error=error_map[exc_name]: _Runner(
                error
            )
            monkeypatch.setitem(
                sys.modules, "providence_core.utils.process", process_mod
            )
            with pytest.raises(typer.Exit) as exc_info:
                test_mod.TestCommand().run(False, False, True, None)
            assert exc_info.value.exit_code == code

    def test_run_wrapper_delegates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _fake_run(
            self,
            verbose: bool,
            fail_fast: bool,
            coverage: bool,
            cov_fail_under: int | None,
        ) -> None:
            captured.update(
                {
                    "verbose": verbose,
                    "fail_fast": fail_fast,
                    "coverage": coverage,
                    "cov_fail_under": cov_fail_under,
                }
            )

        monkeypatch.setattr(test_mod.TestCommand, "run", _fake_run)
        test_mod.run(verbose=True, fail_fast=True, coverage=False, cov_fail_under=77)
        assert captured == {
            "verbose": True,
            "fail_fast": True,
            "coverage": False,
            "cov_fail_under": 77,
        }

    def test_run_missing_script(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: tmp_path)
        with pytest.raises(typer.Exit):
            test_mod.TestCommand().run(False, False, True, None)


class TestCiValidateCommand:
    def test_ci_validate_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        for sub in ("tools/health", "tools/governance", "tools/testing"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        (root / "tools" / "health" / "health_check.py").write_text("", encoding="utf-8")
        (root / "tools" / "governance" / "compliance.py").write_text(
            "", encoding="utf-8"
        )
        (root / "tools" / "testing" / "run-all-tests.py").write_text(
            "", encoding="utf-8"
        )
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        monkeypatch.setattr(test_mod, "_check_import", lambda module: True)
        monkeypatch.setattr(test_mod, "_run_script", lambda *args, **kwargs: 0)
        monkeypatch.setattr(test_mod, "_run_cli", lambda *args, **kwargs: 0)
        monkeypatch.setattr(test_mod, "_run_pytest", lambda *args, **kwargs: 0)
        test_mod.ci_validate(
            health=True, governance=True, tests=True, soak_threads=True
        )

    def test_ci_validate_missing_files_and_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        (root / "tools" / "health").mkdir(parents=True, exist_ok=True)
        (root / "tools" / "testing").mkdir(parents=True, exist_ok=True)
        (root / "tools" / "governance").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        monkeypatch.setattr(test_mod, "_check_import", lambda module: module != "yaml")
        monkeypatch.setattr(test_mod, "_run_script", lambda *args, **kwargs: 1)
        monkeypatch.setattr(test_mod, "_run_cli", lambda *args, **kwargs: 1)
        monkeypatch.setattr(test_mod, "_run_pytest", lambda *args, **kwargs: 1)
        with pytest.raises(typer.Exit):
            test_mod.ci_validate(
                health=True, governance=True, tests=True, soak_threads=True
            )

    def test_ci_validate_runtime_rc_3_accepted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        for sub in ("tools/health", "tools/governance", "tools/testing"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        (root / "tools" / "health" / "health_check.py").write_text("", encoding="utf-8")
        (root / "tools" / "governance" / "compliance.py").write_text(
            "", encoding="utf-8"
        )
        (root / "tools" / "testing" / "run-all-tests.py").write_text(
            "", encoding="utf-8"
        )
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        monkeypatch.setattr(test_mod, "_check_import", lambda module: True)
        monkeypatch.setattr(test_mod, "_run_script", lambda *args, **kwargs: 0)
        responses = iter([0, 3, 0, 0, 0])
        monkeypatch.setattr(
            test_mod, "_run_cli", lambda *args, **kwargs: next(responses)
        )
        monkeypatch.setattr(test_mod, "_run_pytest", lambda *args, **kwargs: 0)
        test_mod.ci_validate(
            health=True, governance=True, tests=True, soak_threads=False
        )

    def test_ci_validate_script_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        for sub in ("tools/health", "tools/governance", "tools/testing"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        (root / "tools" / "health" / "health_check.py").write_text("", encoding="utf-8")
        (root / "tools" / "governance" / "compliance.py").write_text(
            "", encoding="utf-8"
        )
        (root / "tools" / "testing" / "run-all-tests.py").write_text(
            "", encoding="utf-8"
        )
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        monkeypatch.setattr(test_mod, "_check_import", lambda module: True)
        monkeypatch.setattr(test_mod, "_run_cli", lambda *args, **kwargs: 0)
        monkeypatch.setattr(test_mod, "_run_pytest", lambda *args, **kwargs: 0)

        def _run_script(script_path: str, extra_args: list[str], cwd: str) -> int:
            if script_path.endswith("health_check.py"):
                return 1
            if script_path.endswith("compliance.py"):
                return 1
            if script_path.endswith("run-all-tests.py"):
                return 1
            return 0

        monkeypatch.setattr(test_mod, "_run_script", _run_script)
        with pytest.raises(typer.Exit):
            test_mod.ci_validate(
                health=True, governance=True, tests=True, soak_threads=False
            )


class TestReviewGolden:
    def test_helper_branches(self, tmp_path: Path) -> None:
        assert _resolve_golden_path(tmp_path).name == "golden-ast.json"
        assert _find_artifact(tmp_path) is None

    def test_review_golden_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        artifact = root / ".providence" / "compiled" / "governance-core.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}", encoding="utf-8")
        golden = root / ".providence" / "runtime" / "golden-ast.json"
        golden.parent.mkdir(parents=True, exist_ok=True)

        class _Diff:
            breaking_changes = []
            non_breaking_changes = []
            added_items = []
            is_clean = True

            def summary(self) -> str:
                return "clean"

        class _AST:
            items = [1, 2]
            source_fingerprint = "abcdef"

            @classmethod
            def from_compiled_json(cls, path: Path):
                return cls()

            @classmethod
            def from_dict(cls, raw: dict[str, object]):
                return cls()

            def to_json(self) -> str:
                return "{}"

            def diff(self, current: object) -> _Diff:
                return _Diff()

        fake_ast_mod = types.ModuleType("providence_core.governance.ast")
        fake_ast_mod.GovernanceAST = _AST
        monkeypatch.setitem(sys.modules, "providence_core.governance.ast", fake_ast_mod)
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)

        _save_golden(golden, _AST())
        assert golden.exists()
        test_mod.review_golden(
            update=False, fail_on_breaking=True, artifact=artifact, golden=golden
        )

    def test_review_golden_error_and_update_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        artifact = root / ".providence" / "compiled" / "governance-core.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}", encoding="utf-8")

        class _AST:
            items = [1]
            source_fingerprint = "abcdef"

            @classmethod
            def from_compiled_json(cls, path: Path):
                return cls()

            @classmethod
            def from_dict(cls, raw: dict[str, object]):
                return cls()

            def to_json(self) -> str:
                return "{}"

            def diff(self, current: object):
                return types.SimpleNamespace(
                    breaking_changes=[],
                    non_breaking_changes=[],
                    added_items=[],
                    is_clean=True,
                    has_breaking_changes=False,
                    summary=lambda: "clean",
                )

        _install_golden_ast(monkeypatch, current_ast=_AST(), golden_ast=_AST())
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)

        golden = root / ".providence" / "runtime" / "golden-ast.json"
        test_mod.review_golden(
            update=False, fail_on_breaking=True, artifact=artifact, golden=golden
        )
        test_mod.review_golden(
            update=True, fail_on_breaking=True, artifact=artifact, golden=golden
        )
        assert golden.exists()

        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        golden.write_text("{}", encoding="utf-8")
        test_mod.review_golden(
            update=False, fail_on_breaking=True, artifact=artifact, golden=golden
        )

        class _BrokenCurrentAST:
            @classmethod
            def from_compiled_json(cls, path: Path):
                raise ValueError("bad artifact")

        fake_ast_mod = types.ModuleType("providence_core.governance.ast")
        fake_ast_mod.GovernanceAST = _BrokenCurrentAST
        monkeypatch.setitem(sys.modules, "providence_core.governance.ast", fake_ast_mod)
        with pytest.raises(typer.Exit):
            test_mod.review_golden(
                update=False, fail_on_breaking=True, artifact=artifact, golden=golden
            )

    def test_review_golden_import_and_load_error_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        artifact = root / ".providence" / "compiled" / "governance-core.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}", encoding="utf-8")
        golden = root / ".providence" / "runtime" / "golden-ast.json"
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)

        real_import = builtins.__import__

        def _blocked_import(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name == "providence_core.governance.ast":
                raise ImportError("blocked")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _blocked_import)
        with pytest.raises(typer.Exit):
            test_mod.review_golden(
                update=False, fail_on_breaking=True, artifact=artifact, golden=golden
            )
        monkeypatch.setattr(builtins, "__import__", real_import)

    def test_review_golden_load_error_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        artifact = root / ".providence" / "compiled" / "governance-core.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}", encoding="utf-8")
        golden = root / ".providence" / "runtime" / "golden-ast.json"
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text("{}", encoding="utf-8")

        class _CurrentAST:
            def diff(self, current: object):
                return types.SimpleNamespace(
                    breaking_changes=[],
                    non_breaking_changes=[],
                    added_items=[],
                    is_clean=False,
                    has_breaking_changes=False,
                    summary=lambda: "bad",
                )

        class _GovernanceAST:
            @classmethod
            def from_compiled_json(cls, path: Path):
                return _CurrentAST()

            @classmethod
            def from_dict(cls, raw: dict[str, object]):
                raise ValueError("bad golden")

        ast_mod = types.ModuleType("providence_core.governance.ast")
        ast_mod.GovernanceAST = _GovernanceAST
        monkeypatch.setitem(sys.modules, "providence_core.governance.ast", ast_mod)
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        with pytest.raises(typer.Exit):
            test_mod.review_golden(
                update=False, fail_on_breaking=True, artifact=artifact, golden=golden
            )

    def test_review_golden_missing_and_breaking_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        with pytest.raises(typer.Exit):
            test_mod.review_golden(
                update=False, fail_on_breaking=True, artifact=None, golden=None
            )

        artifact = root / ".providence" / "compiled" / "governance-core.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}", encoding="utf-8")
        golden = root / ".providence" / "runtime" / "golden-ast.json"

        class _BreakingDiff:
            breaking_changes = [
                types.SimpleNamespace(
                    item_id="M1", change_type="changed", before=1, after=2
                )
            ]
            non_breaking_changes = [
                types.SimpleNamespace(
                    item_id="M2", field="title", before="old", after="new"
                )
            ]
            added_items = [types.SimpleNamespace(item_id="M3", after="added")]
            is_clean = False
            has_breaking_changes = True

            def summary(self) -> str:
                return "breaking"

        class _AST:
            items = [1]
            source_fingerprint = "abcdef"

            @classmethod
            def from_compiled_json(cls, path: Path):
                return cls()

            @classmethod
            def from_dict(cls, raw: dict[str, object]):
                return cls()

            def to_json(self) -> str:
                return "{}"

            def diff(self, current: object) -> _BreakingDiff:
                return _BreakingDiff()

        _install_golden_ast(monkeypatch, current_ast=_AST(), golden_ast=_AST())
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        test_mod.review_golden(
            update=False, fail_on_breaking=True, artifact=artifact, golden=golden
        )
        golden.write_text("{}", encoding="utf-8")
        with pytest.raises(typer.Exit):
            test_mod.review_golden(
                update=False, fail_on_breaking=True, artifact=artifact, golden=golden
            )
