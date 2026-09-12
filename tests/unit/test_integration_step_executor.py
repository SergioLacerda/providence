from pydantic import TypeAdapter, ValidationError

from providence_integration.engine.context import ExecutionContext
from providence_integration.engine.step_executor import StepExecutor
from providence_integration.engine.types import GenericStep, InvalidStep, StepSpec


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


class DummyAssertion:
    def __init__(self, **kwargs):
        self.success = kwargs.get("success", True)
        self.message = kwargs.get("message", "ok")

    def execute(self, context):
        return type("Result", (), {"success": self.success, "message": self.message})()


def dummy_runner(inputs, context, spec_dir):
    context["ran"] = True


def error_runner(inputs, context, spec_dir):
    raise RuntimeError("fail")


def test_missing_runner_marks_step_failed(tmp_path):
    step = coerce_step({"id": "s", "type": "ghost"})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(runner_registry={}, assertion_registry={})
    result = executor.execute(step, ctx)
    assert not result.success
    assert "runner not found" in result.details
    ctx.cleanup()


def test_runner_exception_marks_step_failed(tmp_path):
    step = coerce_step({"id": "s", "type": "err"})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(
        runner_registry={"err": error_runner}, assertion_registry={}
    )
    result = executor.execute(step, ctx)
    assert not result.success
    assert "runner error" in result.details
    ctx.cleanup()


def test_assertion_not_found_marks_step_failed(tmp_path):
    step = coerce_step({"id": "s", "type": "ok", "asserts": [{"type": "ghost"}]})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(runner_registry={"ok": dummy_runner}, assertion_registry={})
    result = executor.execute(step, ctx)
    assert not result.success
    assert "assertion not found" in result.details
    ctx.cleanup()


def test_assertion_error_marks_step_failed(tmp_path):
    class BrokenAssertion:
        def __init__(self, **kwargs):
            pass

        def execute(self, context):
            raise ValueError("boom")

    step = coerce_step({"id": "s", "type": "ok", "asserts": [{"type": "broken"}]})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(
        runner_registry={"ok": dummy_runner},
        assertion_registry={"broken": BrokenAssertion},
    )
    result = executor.execute(step, ctx)
    assert not result.success
    assert "assertion error" in result.details
    assert "boom" in result.details
    ctx.cleanup()


def test_failing_assertion_marks_step_failed(tmp_path):
    step = coerce_step(
        {
            "id": "s",
            "type": "ok",
            "asserts": [{"type": "fail", "success": False, "message": "fail!"}],
        }
    )
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(
        runner_registry={"ok": dummy_runner},
        assertion_registry={"fail": DummyAssertion},
    )
    result = executor.execute(step, ctx)
    assert not result.success
    assert "fail!" in result.details
    ctx.cleanup()


def test_successful_step_and_assertion(tmp_path):
    step = coerce_step(
        {
            "id": "s",
            "type": "ok",
            "asserts": [{"type": "pass", "success": True, "message": "yay"}],
        }
    )
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(
        runner_registry={"ok": dummy_runner},
        assertion_registry={"pass": DummyAssertion},
    )
    result = executor.execute(step, ctx)
    assert result.success
    assert "yay" in result.details
    ctx.cleanup()


def test_step_with_no_asserts_succeeds(tmp_path):
    step = coerce_step({"id": "bare", "type": "ok"})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(runner_registry={"ok": dummy_runner}, assertion_registry={})
    result = executor.execute(step, ctx)
    assert result.success
    ctx.cleanup()


def test_context_side_effect(tmp_path):
    step = coerce_step({"id": "s", "type": "ok"})
    ctx = ExecutionContext.from_spec({}, tmp_path)
    executor = StepExecutor(runner_registry={"ok": dummy_runner}, assertion_registry={})
    executor.execute(step, ctx)
    assert ctx.as_dict()["ran"] is True
    ctx.cleanup()
