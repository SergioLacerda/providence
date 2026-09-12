"""ISkillLifecycle contract tests for the shared `Handler` base class (A4).

Every skill handler must provide a uniform pre_run/post_run/timeout_hook/
retry_hook lifecycle without relying on hasattr() duck-typing in the executor,
so initialization and cleanup stay consistent across handlers.
"""

from __future__ import annotations

from providence_runtime._skill_executor import Handler, PreRunOutcome
from providence_runtime._skill_executor._base import BaseSkillHandler


def test_base_skill_handler_is_alias_for_handler() -> None:
    assert BaseSkillHandler is Handler


def test_default_pre_run_is_a_no_op_outcome() -> None:
    handler = Handler()
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert isinstance(outcome, PreRunOutcome)
    assert outcome.artifacts == {}
    assert outcome.early_result is None
    assert outcome.compose_config is None


def test_default_post_run_returns_empty_artifacts() -> None:
    handler = Handler()
    result = handler.post_run({}, learning=None, exit_code=0, artifacts={})
    assert result == {}


def test_subclass_without_pre_run_override_still_conforms_to_lifecycle() -> None:
    class _MinimalHandler(Handler):
        pass

    handler = _MinimalHandler()
    assert hasattr(handler, "pre_run")
    assert hasattr(handler, "post_run")
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert outcome.early_result is None
