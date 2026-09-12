"""Base handler lifecycle hooks and execution context primitives."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from providence_skills import SkillRunResult

from .._skill_contracts import SkillDefinition
from ..learning import FailureLedgerEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-run outcome
# ---------------------------------------------------------------------------


@dataclass
class PreRunOutcome:
    artifacts: dict[str, Any] = field(default_factory=dict)
    early_result: SkillRunResult | None = None
    compose_config: dict[str, Any] | None = None


class Handler:
    """Base skill handler lifecycle hooks (the project's ISkillLifecycle contract).

    Every concrete skill handler inherits from this class and gets uniform
    pre_run/post_run/can_retry/retry_hook/timeout_hook lifecycle methods, so
    the executor can invoke them unconditionally instead of relying on
    hasattr() duck-typing. Subclasses override only the hooks they need;
    the defaults are no-ops.

    Example:
        Subclasses override `pre_run`, `post_run`, `can_retry`, `retry_hook`,
        or `timeout_hook` to extend governed execution without changing the
        executor template.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: SkillDefinition | None,
        profile: str,
        footer_fn: Any,
    ) -> PreRunOutcome:
        del context, learning, skill, profile, footer_fn
        return PreRunOutcome()

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        del context, learning, exit_code, artifacts
        return {}

    def can_retry(
        self,
        context: dict[str, Any],
        *,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> bool:
        del context, exit_code, error, attempt_count
        return False

    def retry_hook(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: SkillDefinition,
        command: str,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> dict[str, Any]:
        del context
        if learning is not None and hasattr(learning, "append_failure"):
            learning.append_failure(
                FailureLedgerEntry(
                    symptom="retry",
                    root_cause=f"{skill.name}:{command}",
                    fix="automatic_retry",
                    validation=f"attempt_{attempt_count}",
                    regression=exit_code != 0,
                    tags=["retry", skill.name],
                    evidence_refs=[error] if error else [],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        return {
            "retry_event": {
                "skill": skill.name,
                "command": command,
                "exit_code": exit_code,
                "error": error,
                "attempt_count": attempt_count,
            }
        }

    def timeout_hook(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: SkillDefinition,
        elapsed_seconds: int,
    ) -> dict[str, Any]:
        if learning is not None and hasattr(learning, "append_failure"):
            learning.append_failure(
                FailureLedgerEntry(
                    symptom="timeout",
                    root_cause=f"skill {skill.name} exceeded {elapsed_seconds}s",
                    fix="retry_with_lower_budget",
                    validation="timeout_hook",
                    regression=True,
                    tags=["timeout", skill.name],
                    evidence_refs=[],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        return {
            "timeout_event": {
                "skill": skill.name,
                "elapsed_seconds": elapsed_seconds,
                "action": "retry_with_lower_budget",
            }
        }


# Alias exposing the project's public name for the skill lifecycle contract.
BaseSkillHandler = Handler


class ContextCarrier:
    def __init__(self, initial_context: dict[str, Any] | None = None) -> None:
        self._layers: list[dict[str, Any]] = []
        self._layer_metadata: list[dict[str, str]] = []
        if initial_context:
            self.push_layer(initial_context, source="initial", skill_name="initial")

    def push_layer(
        self,
        layer: dict[str, Any],
        *,
        source: str,
        skill_name: str,
    ) -> None:
        self._layers.append(dict(layer))
        self._layer_metadata.append({"source": source, "skill": skill_name})
        logger.debug(
            "[ContextCarrier] push_layer source=%s skill=%s keys=%s total_layers=%s",
            source,
            skill_name,
            sorted(layer.keys()),
            len(self._layers),
        )

    def get(self, key: str, default: Any = None) -> Any:
        for layer in reversed(self._layers):
            if key in layer:
                return layer[key]
        return default

    def get_with_source(self, key: str) -> tuple[Any, str | None]:
        for index in range(len(self._layers) - 1, -1, -1):
            layer = self._layers[index]
            if key in layer:
                metadata = self._layer_metadata[index]
                return layer[key], metadata.get("skill")
        return None, None

    def snapshot(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for layer in self._layers:
            merged.update(layer)
        return merged

    def audit_trail(self, key: str) -> list[tuple[Any, str | None]]:
        trail: list[tuple[Any, str | None]] = []
        for index in range(len(self._layers)):
            layer = self._layers[index]
            if key in layer:
                metadata = self._layer_metadata[index]
                trail.append((layer[key], metadata.get("skill")))
        return trail
