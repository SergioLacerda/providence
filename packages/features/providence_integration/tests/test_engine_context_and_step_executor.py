"""
Unit tests for ExecutionContext and StepExecutor.

Covers:
- ExecutionContext lifecycle (from_spec, as_dict, cleanup)
- Isolation/temp-dir behaviour
- StepExecutor: happy path, runner error, missing runner,
  missing assertion, assertion runtime error, step with no asserts.

Run:
    pytest tests/unit/execution/test_engine_context_and_step_executor.py -v
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from providence_integration.assertions.result import AssertionResult
from providence_integration.engine.context import ExecutionContext
from providence_integration.engine.step_executor import StepExecutor
from providence_integration.engine.types import GenericStep, InvalidStep, StepSpec

SpecDict = dict[str, Any]
ContextDict = dict[str, Any]
RunnerFn = Callable[[SpecDict, ContextDict, Path], None]
AssertionCls = type[Any]


# ---------------------------------------------------------------------------
# Helper: coerce dict to Pydantic model
# ---------------------------------------------------------------------------


def coerce_step(raw_step: dict) -> StepSpec:
    """Convert a dict to a proper Pydantic model instance."""
    adapter: TypeAdapter[StepSpec] = TypeAdapter(GenericStep)
    try:
        # Try to parse as generic step (works for any step type)
        return adapter.validate_python(raw_step)
    except ValidationError as e:
        # Return InvalidStep with error details on validation failure
        return InvalidStep(
            type=raw_step.get("type", "unknown"),
            inputs=raw_step.get("inputs", {}),
            id=raw_step.get("id", ""),
            asserts=raw_step.get("asserts", []),
            parse_error=str(e),
        )


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_context(spec: SpecDict, spec_dir: Path) -> ExecutionContext:
    return ExecutionContext.from_spec(spec, spec_dir)


def _passing_runner(_inputs: SpecDict, _context: ContextDict, _spec_dir: Path) -> None:
    """Runner that succeeds silently."""


def _failing_runner(_inputs: SpecDict, _context: ContextDict, _spec_dir: Path) -> None:
    raise RuntimeError("boom from runner")


def _side_effect_runner(
    _inputs: SpecDict, context: ContextDict, _spec_dir: Path
) -> None:
    """Runner that writes to context so assertions can check it."""
    context["last_exit_code"] = 0


def _make_assertion_cls(success: bool, message: str) -> AssertionCls:
    """Return a dummy assertion class whose execute() returns a fixed result."""

    class _Assertion:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def execute(self, _context: ContextDict) -> AssertionResult:
            return AssertionResult(success, message)

    return _Assertion


def _make_executor(
    runner_map: dict[str, RunnerFn] | None = None,
    assertion_map: dict[str, AssertionCls] | None = None,
) -> StepExecutor:
    return StepExecutor(
        runner_registry=runner_map or {},
        assertion_registry=assertion_map or {},
    )


# ---------------------------------------------------------------------------
# ExecutionContext — construction
# ---------------------------------------------------------------------------


class TestExecutionContextConstruction:
    def test_no_context_block_uses_cwd(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        assert ctx.working_dir == Path.cwd()
        assert not ctx.isolation_enabled
        assert ctx._temp_dir is None
        ctx.cleanup()

    def test_isolation_true_creates_temp_dir(self, spec_dir: Path) -> None:
        ctx = _make_context({"context": {"isolation": True}}, spec_dir)
        assert ctx.isolation_enabled
        assert ctx._temp_dir is not None
        assert ctx._temp_dir.exists()
        ctx.cleanup()

    def test_working_dir_temp_creates_temp_dir(self, spec_dir: Path) -> None:
        ctx = _make_context({"context": {"working_dir": "temp"}}, spec_dir)
        assert ctx.isolation_enabled
        assert ctx._temp_dir is not None
        assert ctx._temp_dir.exists()
        ctx.cleanup()

    def test_explicit_working_dir_used(self, spec_dir: Path, tmp_path: Path) -> None:
        target = tmp_path / "custom_wd"
        ctx = _make_context({"context": {"working_dir": str(target)}}, spec_dir)
        assert ctx.working_dir == target
        assert ctx._temp_dir is None
        assert target.exists()
        ctx.cleanup()

    def test_spec_dir_stored(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        assert ctx.spec_dir == spec_dir
        ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — as_dict
# ---------------------------------------------------------------------------


class TestExecutionContextAsDict:
    def test_as_dict_contains_working_dir(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        d = ctx.as_dict()
        assert "working_dir" in d
        assert d["working_dir"] == ctx.working_dir
        ctx.cleanup()

    def test_as_dict_is_shared_mutable_state(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        ctx.as_dict()["foo"] = "bar"
        assert ctx.data["foo"] == "bar"
        ctx.cleanup()


# ---------------------------------------------------------------------------
# ExecutionContext — cleanup
# ---------------------------------------------------------------------------


class TestExecutionContextCleanup:
    def test_cleanup_removes_temp_dir(self, spec_dir: Path) -> None:
        ctx = _make_context({"context": {"isolation": True}}, spec_dir)
        temp = ctx._temp_dir
        assert temp is not None
        assert temp.exists()
        ctx.cleanup()
        assert not temp.exists()

    def test_cleanup_sets_temp_dir_to_none(self, spec_dir: Path) -> None:
        ctx = _make_context({"context": {"isolation": True}}, spec_dir)
        ctx.cleanup()
        assert ctx._temp_dir is None

    def test_cleanup_is_idempotent(self, spec_dir: Path) -> None:
        ctx = _make_context({"context": {"isolation": True}}, spec_dir)
        ctx.cleanup()
        ctx.cleanup()  # must not raise

    def test_cleanup_no_op_when_no_temp_dir(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        ctx.cleanup()  # must not raise
        assert ctx._temp_dir is None


# ---------------------------------------------------------------------------
# StepExecutor — happy path
# ---------------------------------------------------------------------------


class TestStepExecutorHappyPath:
    def test_passing_runner_and_assertion(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"my.runner": _passing_runner},
            assertion_map={"my.assert": _make_assertion_cls(True, "all good")},
        )
        step = coerce_step(
            {
                "id": "step1",
                "type": "my.runner",
                "inputs": {},
                "asserts": [{"type": "my.assert"}],
            }
        )
        result = executor.execute(step, ctx)
        assert result.success is True
        assert result.name == "step1"
        assert "all good" in result.details
        ctx.cleanup()

    def test_step_with_no_asserts_succeeds(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(runner_map={"my.runner": _passing_runner})
        step = coerce_step({"id": "bare_step", "type": "my.runner", "inputs": {}})
        result = executor.execute(step, ctx)
        assert result.success is True
        ctx.cleanup()

    def test_step_id_defaults_to_unnamed(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(runner_map={"my.runner": _passing_runner})
        result = executor.execute(coerce_step({"type": "my.runner"}), ctx)
        assert result.name == "unnamed_step"
        ctx.cleanup()

    def test_multiple_assertions_all_pass(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"r": _passing_runner},
            assertion_map={
                "a1": _make_assertion_cls(True, "a1 ok"),
                "a2": _make_assertion_cls(True, "a2 ok"),
            },
        )
        step = coerce_step(
            {
                "id": "multi",
                "type": "r",
                "asserts": [{"type": "a1"}, {"type": "a2"}],
            }
        )
        result = executor.execute(step, ctx)
        assert result.success is True
        assert "a1 ok" in result.details
        assert "a2 ok" in result.details
        ctx.cleanup()


# ---------------------------------------------------------------------------
# StepExecutor — runner failures
# ---------------------------------------------------------------------------


class TestStepExecutorRunnerFailures:
    def test_missing_runner_marks_step_failed(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor()
        result = executor.execute(
            coerce_step({"id": "s", "type": "nonexistent.runner"}), ctx
        )
        assert result.success is False
        assert "runner not found" in result.details
        ctx.cleanup()

    def test_runner_exception_marks_step_failed(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(runner_map={"bad.runner": _failing_runner})
        result = executor.execute(coerce_step({"id": "s", "type": "bad.runner"}), ctx)
        assert result.success is False
        assert "runner error" in result.details
        assert "boom from runner" in result.details
        ctx.cleanup()

    def test_runner_exception_still_runs_assertions(self, spec_dir: Path) -> None:
        """Assertions execute even when runner raised."""
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"bad.runner": _failing_runner},
            assertion_map={"a": _make_assertion_cls(True, "a ok")},
        )
        step = coerce_step(
            {"id": "s", "type": "bad.runner", "asserts": [{"type": "a"}]}
        )
        result = executor.execute(step, ctx)
        # runner failed → overall failure, but assertion message still present
        assert result.success is False
        assert "a ok" in result.details
        ctx.cleanup()


# ---------------------------------------------------------------------------
# StepExecutor — assertion failures
# ---------------------------------------------------------------------------


class TestStepExecutorAssertionFailures:
    def test_failing_assertion_marks_step_failed(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"r": _passing_runner},
            assertion_map={"bad.a": _make_assertion_cls(False, "not ok")},
        )
        step = coerce_step({"id": "s", "type": "r", "asserts": [{"type": "bad.a"}]})
        result = executor.execute(step, ctx)
        assert result.success is False
        assert "not ok" in result.details
        ctx.cleanup()

    def test_missing_assertion_type_marks_step_failed(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(runner_map={"r": _passing_runner})
        step = coerce_step(
            {"id": "s", "type": "r", "asserts": [{"type": "ghost.assert"}]}
        )
        result = executor.execute(step, ctx)
        assert result.success is False
        assert "assertion not found" in result.details
        ctx.cleanup()

    def test_assertion_runtime_error_marks_step_failed(self, spec_dir: Path) -> None:
        class _BrokenAssertion:
            def __init__(self, **_kwargs: Any) -> None:
                pass

            def execute(self, _context: ContextDict) -> AssertionResult:
                raise ValueError("assertion exploded")

        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"r": _passing_runner},
            assertion_map={"broken.a": _BrokenAssertion},
        )
        step = coerce_step({"id": "s", "type": "r", "asserts": [{"type": "broken.a"}]})
        result = executor.execute(step, ctx)
        assert result.success is False
        assert "assertion error" in result.details
        assert "assertion exploded" in result.details
        ctx.cleanup()

    def test_one_failing_assertion_out_of_many(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"r": _passing_runner},
            assertion_map={
                "ok.a": _make_assertion_cls(True, "a ok"),
                "fail.a": _make_assertion_cls(False, "a fail"),
            },
        )
        step = coerce_step(
            {
                "id": "s",
                "type": "r",
                "asserts": [{"type": "ok.a"}, {"type": "fail.a"}],
            }
        )
        result = executor.execute(step, ctx)
        assert result.success is False
        assert "a ok" in result.details
        assert "a fail" in result.details
        ctx.cleanup()


# ---------------------------------------------------------------------------
# StepExecutor — context side-effects
# ---------------------------------------------------------------------------


class TestStepExecutorContextSideEffects:
    def test_runner_can_write_to_context(self, spec_dir: Path) -> None:
        ctx = _make_context({}, spec_dir)
        executor = _make_executor(runner_map={"r": _side_effect_runner})
        executor.execute(coerce_step({"id": "s", "type": "r"}), ctx)
        assert ctx.as_dict().get("last_exit_code") == 0
        ctx.cleanup()

    def test_assertion_receives_runner_side_effects(self, spec_dir: Path) -> None:
        """Assertions see context state written by the runner."""
        recorded: list[int | None] = []

        class _ContextCapture:
            def __init__(self, **_kwargs: Any) -> None:
                pass

            def execute(self, context: ContextDict) -> AssertionResult:
                recorded.append(context.get("last_exit_code"))
                return AssertionResult(True, "captured")

        ctx = _make_context({}, spec_dir)
        executor = _make_executor(
            runner_map={"r": _side_effect_runner},
            assertion_map={"capture": _ContextCapture},
        )
        executor.execute(
            coerce_step({"id": "s", "type": "r", "asserts": [{"type": "capture"}]}), ctx
        )
        assert recorded == [0]
        ctx.cleanup()
