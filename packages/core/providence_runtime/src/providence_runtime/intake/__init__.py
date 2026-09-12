"""Governed Intake — intent classification, entrypoint/gate/routing resolution.

Extracted from `providence_cli.services.ask_response_intake` per
`.analysis/pending/20260907-backend-governance-reorg-refinement` (Fase 1 of
the backend governance reorganization roadmap,
`docs/migration/2026-09-07-backend-governance-reorg-roadmap.md`). The old
module keeps thin re-export shims at its original path — existing callers
and test `mock.patch` targets keep working unmodified.
"""

from __future__ import annotations

from .contract_builder import build_intake_contract_fields
from .entrypoint import ASK_ENTRYPOINT_ENV, resolve_ask_entrypoint
from .gate import resolve_execution_gate
from .intent import _looks_like_implementation_intent, classify_ask_intent
from .routing import resolve_ask_next_action

__all__ = [
    "ASK_ENTRYPOINT_ENV",
    "build_intake_contract_fields",
    "classify_ask_intent",
    "resolve_ask_entrypoint",
    "resolve_ask_next_action",
    "resolve_execution_gate",
    "_looks_like_implementation_intent",
]
