"""TelemetrySink — collects runtime events with optional JSONL persistence."""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import fcntl
except ImportError:  # pragma: no cover — fcntl is POSIX-only (no Windows)
    fcntl = None  # type: ignore[assignment]

from .._events import RuntimeEvent
from ..validator import TraceabilityValidator
from ._constants import (
    _MANDATORY_EVENTS,
    _ZONE_BREACH_PCT,
    _ZONE_RED_PCT,
    ECONOMY_BUDGET_BREACH,
    ECONOMY_BUDGET_WARN,
    ECONOMY_COMPRESSION_SKIP,
    MODE_ACTIVE,
    MODE_PASSIVE,
    MODE_STRICT,
)
from ._economy_enrichment import _enrich_economy

if TYPE_CHECKING:
    from ..alerts import AlertDispatcher

logger = logging.getLogger(__name__)


class TelemetrySink:
    """Collects runtime events; optionally persists them to a JSONL file.

    Parameters
    ----------
    jsonl_path:
        Base path for the JSONL file.  When *segment_by_work_item* is True,
        events are written to ``{jsonl_path.parent}/{work_item_id}.jsonl``
        instead of directly to *jsonl_path*.
    logging_mode:
        Controls verbosity.  In ``passive`` mode only mandatory events are
        written to the JSONL file; all events remain in the in-memory list.
    segment_by_work_item:
        When True, segment the JSONL output by ``work_item_id`` from each
        event's ``details`` dict (§15.1 item 5 — task-scoped segmentation).
    agent_id:
        Identifier for the agent/CLI instance emitting events. If not provided,
        defaults to ``SDD_AGENT_ID`` environment variable or "unknown".
    alert_dispatcher:
        Fase 2: Optional AlertDispatcher for event-triggered webhooks.
        Dispatch is best-effort; all exceptions suppressed.
    """

    def __init__(
        self,
        jsonl_path: Path | None = None,
        logging_mode: str = MODE_PASSIVE,
        segment_by_work_item: bool = False,
        agent_id: str | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        import uuid

        self._events: list[RuntimeEvent] = []
        self._persisted_event_ids: set[int] = set()
        self._jsonl_path = jsonl_path
        self._logging_mode = logging_mode
        self._segment_by_work_item = segment_by_work_item
        # Phase 0 fix: Populate agent_id from parameter, env var, or session UUID
        self._agent_id = (
            agent_id
            or os.environ.get("SDD_AGENT_ID")
            or f"session-{str(uuid.uuid4())[:8]}"
        )
        # Fase 2: optional alert dispatcher (best-effort side-car)
        self._alert_dispatcher = alert_dispatcher
        self._traceability_validator = TraceabilityValidator()

    def emit(self, event: RuntimeEvent) -> None:
        """Record *event* in memory and conditionally persist to JSONL."""
        # Phase 0 fix: Populate agent_id if not already set
        if not event.agent_id:
            event.agent_id = self._agent_id
        _enrich_economy(event)
        self._events.append(event)
        if self._jsonl_path is not None:
            self._write_jsonl(event)
        self._maybe_emit_zone_event(event)
        # Fase 2: alert dispatch is best-effort, never blocks or raises
        if self._alert_dispatcher is not None:
            with contextlib.suppress(Exception):
                self._alert_dispatcher.on_event(event)

    def list_events(self) -> list[RuntimeEvent]:
        """List Events."""
        return list(self._events)

    def flush(self) -> None:
        """Force-write all pending in-memory events to the JSONL sink.

        No-op when no *jsonl_path* is configured.
        """
        if self._jsonl_path is None:
            return
        for evt in self._events:
            self._write_jsonl(evt)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _maybe_emit_zone_event(self, source_event: RuntimeEvent) -> None:
        """Auto-emit economy.budget.warn, economy.budget.breach, or economy.compression.skip.

        Fires after the source event is already recorded.  Zone events are
        appended directly (bypassing :meth:`emit`) to prevent recursion.
        Only fires when *budget_utilization_pct* is known and the source
        event itself is not already a zone event.
        """
        pct = source_event.budget_utilization_pct
        if pct is None:
            return
        # Do not emit zone events for zone events (prevent infinite recursion).
        if source_event.event in (
            ECONOMY_BUDGET_WARN,
            ECONOMY_BUDGET_BREACH,
            ECONOMY_COMPRESSION_SKIP,
        ):
            return

        if pct >= _ZONE_BREACH_PCT:
            zone_event_name = ECONOMY_BUDGET_BREACH
        elif pct > _ZONE_RED_PCT:
            zone_event_name = ECONOMY_BUDGET_WARN
        elif 70.0 <= pct <= _ZONE_RED_PCT and source_event.compression_ratio is None:
            # YELLOW zone and no compression occurred — emit skip event
            zone_event_name = ECONOMY_COMPRESSION_SKIP
        else:
            return  # GREEN zone or YELLOW with compression already applied

        zone_event = RuntimeEvent(
            event=zone_event_name,
            command=source_event.command,
            status="warn" if zone_event_name != ECONOMY_COMPRESSION_SKIP else "info",
            trace_id=source_event.trace_id,
            workspace_id=source_event.workspace_id,
            agent_id=source_event.agent_id or self._agent_id,
            artifact_fingerprint=source_event.artifact_fingerprint,
            schema_version=source_event.schema_version,
            path_id=source_event.path_id,
            context_bytes_loaded=source_event.context_bytes_loaded,
            context_budget_bytes=source_event.context_budget_bytes,
            budget_utilization_pct=pct,
            details={"source_event": source_event.event},
        )
        self._events.append(zone_event)
        if self._jsonl_path is not None:
            self._write_jsonl(zone_event)

    def _should_persist(self, event: RuntimeEvent) -> bool:
        if self._logging_mode in (MODE_ACTIVE, MODE_STRICT):
            return True
        # passive — only mandatory events
        return event.event in _MANDATORY_EVENTS

    def _resolve_path(self, event: RuntimeEvent) -> Path:
        """Return the actual JSONL file path, respecting work_item segmentation."""
        if self._jsonl_path is None:
            raise RuntimeError("TelemetrySink jsonl_path is required for persistence")
        if not self._segment_by_work_item or not event.details.get("work_item_id"):
            return self._jsonl_path
        work_item_id = str(event.details["work_item_id"])
        # Sanitise to prevent path traversal.
        safe_id = "".join(c for c in work_item_id if c.isalnum() or c in "-_")
        return self._jsonl_path.parent / f"{safe_id}.jsonl"

    def _write_jsonl(self, event: RuntimeEvent) -> None:
        if not self._should_persist(event):
            return
        # Guard against duplicate writes when both `emit()` and a later
        # `flush()` call attempt to persist the same event object.
        if id(event) in self._persisted_event_ids:
            return
        # TEL-01 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
        # `TraceabilityValidator` existed but was never invoked at the
        # emission boundary, so a sensitive event missing its required
        # trace/workspace/agent/source-refs fields would be persisted (and
        # exported) exactly like a compliant one, with no visible signal.
        # This does not block the write (telemetry stays best-effort per the
        # sink's own design) — it makes the existing gap loudly observable
        # instead of silent.
        result = self._traceability_validator.validate_event(event)
        if not result.valid:
            logger.warning(
                "Telemetry event %r is missing required traceability fields: %s",
                event.event,
                result.missing_fields,
            )
        target = self._resolve_path(event)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            # Exclusive advisory lock so concurrent writers (multiple agent
            # processes appending to the same segment) never interleave
            # partial lines; released automatically when the file closes.
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            fh.write(event.to_json() + "\n")
            fh.flush()
            # fsync forces the append to disk before returning, so a crash
            # right after emit() can't lose an event that only ever lived in
            # the page cache — the JSONL sink is the audit source of truth.
            os.fsync(fh.fileno())
        self._persisted_event_ids.add(id(event))
