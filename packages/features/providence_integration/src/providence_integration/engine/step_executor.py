"""Step Executor."""

from __future__ import annotations

from dataclasses import dataclass

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.registry import REGISTRY
from providence_integration.engine.context import ExecutionContext
from providence_integration.engine.types import InvalidStep, RunnerCallable, StepSpec
from providence_integration.runners import RUNNER_REGISTRY

AssertionFactory = type[Assertion]


@dataclass
class StepResult:
    """StepResult."""

    name: str
    success: bool
    messages: list[str]
    runner_status: str | None = None
    assertion_statuses: dict[str, str] | None = None
    error_code: str | None = None

    @property
    def details(self) -> str:
        """Details."""
        return " | ".join(self.messages) or "step executed"


class StepExecutor:
    """Executes a single protocol step with runners and assertions."""

    def __init__(
        self,
        runner_registry: dict[str, RunnerCallable] | None = None,
        assertion_registry: dict[str, AssertionFactory] | None = None,
    ):
        self.runner_registry = runner_registry or RUNNER_REGISTRY
        self.assertion_registry = assertion_registry or REGISTRY

    def execute(self, step: StepSpec, context: ExecutionContext) -> StepResult:
        """Execute."""
        step_name = step.id or "unnamed_step"
        step_type = step.type
        inputs = step.inputs

        step_success = True
        messages: list[str] = []
        assertion_statuses: dict[str, str] = {}
        runner_status = "ok"
        error_code: str | None = None

        # Input validation failed at parse time (Pydantic ValidationError)
        if isinstance(step, InvalidStep):
            return StepResult(
                name=step_name,
                success=False,
                messages=[step.parse_error],
                runner_status="invalid_inputs",
                error_code="invalid_inputs",
            )

        runner = self.runner_registry.get(step_type)
        if runner is None:
            step_success = False
            runner_status = "not_found"
            error_code = "runner_not_found"
            messages.append(f"runner not found: {step_type}")
        else:
            try:
                runner(inputs, context.as_dict(), context.spec_dir)
            except Exception as exc:
                step_success = False
                runner_status = "error"
                error_code = "runner_error"
                messages.append(f"runner error: {exc}")

        for assertion_config in step.asserts:
            assertion_type = assertion_config.type
            assertion_cls = self.assertion_registry.get(assertion_type)
            if assertion_cls is None:
                step_success = False
                assertion_statuses[assertion_type or "<missing-type>"] = "not_found"
                error_code = error_code or "assertion_not_found"
                messages.append(f"assertion not found: {assertion_type}")
                continue

            try:
                assertion = assertion_cls(**assertion_config.model_dump())
                result = assertion.execute(context.as_dict())
            except Exception as exc:
                step_success = False
                assertion_statuses[assertion_type] = "error"
                error_code = error_code or "assertion_error"
                messages.append(f"assertion error ({assertion_type}): {exc}")
                continue

            if not result.success:
                step_success = False
                assertion_statuses[assertion_type] = "failed"
                error_code = error_code or "assertion_failed"
            else:
                assertion_statuses[assertion_type] = "ok"
            messages.append(result.message)

        return StepResult(
            name=step_name,
            success=step_success,
            messages=messages,
            runner_status=runner_status,
            assertion_statuses=assertion_statuses,
            error_code=error_code,
        )
