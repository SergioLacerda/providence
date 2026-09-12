"""AskHandler — governed ask execution contracts and ledger entries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ...learning import FailureLedgerEntry
from .._base import Handler, PreRunOutcome
from .._constants import _FooterFn
from .._context_builders import _build_execution_contract


class AskHandler(Handler):
    """Prepare governed ask execution contracts and ledger entries.

    Example:
        Inject recent failures into `historical_context` before running the
        fallback commands, then record the ask outcome in the learning ledger.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        execution_contract = _build_execution_contract(context)
        recent_failures = (
            learning.list_failures(limit=3)
            if learning is not None and hasattr(learning, "list_failures")
            else []
        )
        active_rules = (
            learning.list_active_rules()
            if learning is not None and hasattr(learning, "list_active_rules")
            else []
        )
        if recent_failures or active_rules:
            execution_contract["historical_context"] = {
                "recent_failures": recent_failures,
                "active_rules": active_rules,
            }
        return PreRunOutcome(artifacts={"execution_contract": execution_contract})

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        contract = artifacts.get(
            "execution_contract", context.get("execution_contract", {})
        )
        if not isinstance(contract, dict):
            contract = {}
        if learning is None or not hasattr(learning, "append_failure"):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(contract.get("task_type", "unspecified")),
                root_cause=str(contract.get("goal", "unspecified")),
                fix="sdd-ask",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["ask", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {}
