"""Token Economy tests — Phase 2 active population.

Covers:
  - Auto-fill of context_budget_bytes from path_id
  - Auto-computation of budget_utilization_pct
  - Auto-computation of tokens_total
  - Auto-emission of economy.budget.warn (RED zone only: > 90%)
  - Auto-emission of economy.budget.breach (BREACH zone: >= 100%)
  - No zone event for GREEN zone (0–70%) or YELLOW zone (71–90%)
  - No recursion when zone events are emitted
  - Pre-set fields are never overwritten (idempotency)
"""

from __future__ import annotations

from providence_runtime import RuntimeEvent, TelemetrySink
from providence_runtime.telemetry import (
    _PATH_BUDGET_BYTES,
    _ZONE_RED_PCT,
    ECONOMY_BUDGET_BREACH,
    ECONOMY_BUDGET_WARN,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    path_id: str = "",
    context_bytes_loaded: int | None = None,
    context_budget_bytes: int | None = None,
    budget_utilization_pct: float | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    tokens_total: int | None = None,
    event: str = "runtime.session.start",
) -> RuntimeEvent:
    return RuntimeEvent(
        event=event,
        command="test",
        status="ok",
        trace_id="trace-economy-test",
        workspace_id="ws-test",
        agent_id="agent-test",
        path_id=path_id,
        context_bytes_loaded=context_bytes_loaded,
        context_budget_bytes=context_budget_bytes,
        budget_utilization_pct=budget_utilization_pct,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        tokens_total=tokens_total,
    )


def _sink() -> TelemetrySink:
    return TelemetrySink(jsonl_path=None, logging_mode="active")


# ---------------------------------------------------------------------------
# PATH budget lookup
# ---------------------------------------------------------------------------


class TestPathBudgetBytes:
    def test_path_a_budget(self) -> None:
        assert _PATH_BUDGET_BYTES["A"] == 40 * 1024

    def test_path_b_budget(self) -> None:
        assert _PATH_BUDGET_BYTES["B"] == 45 * 1024

    def test_path_c_budget(self) -> None:
        assert _PATH_BUDGET_BYTES["C"] == 85 * 1024

    def test_path_d_budget(self) -> None:
        assert _PATH_BUDGET_BYTES["D"] == 35 * 1024


# ---------------------------------------------------------------------------
# _enrich_economy — context_budget_bytes auto-fill
# ---------------------------------------------------------------------------


class TestEnrichContextBudgetBytes:
    def test_auto_fills_budget_bytes_from_path_a(self) -> None:
        evt = _make_event(path_id="A")
        _sink().emit(evt)
        assert evt.context_budget_bytes == 40 * 1024

    def test_auto_fills_budget_bytes_from_path_c(self) -> None:
        evt = _make_event(path_id="C")
        _sink().emit(evt)
        assert evt.context_budget_bytes == 85 * 1024

    def test_does_not_overwrite_explicit_budget_bytes(self) -> None:
        explicit = 99_999
        evt = _make_event(path_id="A", context_budget_bytes=explicit)
        _sink().emit(evt)
        assert evt.context_budget_bytes == explicit

    def test_unknown_path_id_leaves_budget_bytes_none(self) -> None:
        evt = _make_event(path_id="Z")
        _sink().emit(evt)
        assert evt.context_budget_bytes is None

    def test_empty_path_id_leaves_budget_bytes_none(self) -> None:
        evt = _make_event(path_id="")
        _sink().emit(evt)
        assert evt.context_budget_bytes is None


# ---------------------------------------------------------------------------
# _enrich_economy — budget_utilization_pct auto-computation
# ---------------------------------------------------------------------------


class TestEnrichBudgetUtilization:
    def test_computes_utilization_from_bytes(self) -> None:
        budget = 40 * 1024  # 40 KB
        loaded = 20 * 1024  # 20 KB → 50%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        _sink().emit(evt)
        assert evt.budget_utilization_pct == 50.0

    def test_computes_utilization_via_path_id(self) -> None:
        # path_id="A" → budget=40*1024; load half
        loaded = 20 * 1024
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        _sink().emit(evt)
        assert evt.budget_utilization_pct == 50.0

    def test_utilization_rounds_to_two_decimal_places(self) -> None:
        evt = _make_event(context_bytes_loaded=1, context_budget_bytes=3)
        _sink().emit(evt)
        assert evt.budget_utilization_pct == round(1 / 3 * 100, 2)

    def test_does_not_overwrite_explicit_utilization(self) -> None:
        evt = _make_event(
            context_bytes_loaded=100,
            context_budget_bytes=1000,
            budget_utilization_pct=99.9,  # pre-set — must not change
        )
        _sink().emit(evt)
        assert evt.budget_utilization_pct == 99.9

    def test_no_computation_when_budget_bytes_missing(self) -> None:
        evt = _make_event(context_bytes_loaded=100)
        _sink().emit(evt)
        assert evt.budget_utilization_pct is None

    def test_no_computation_when_loaded_bytes_missing(self) -> None:
        evt = _make_event(context_budget_bytes=1000)
        _sink().emit(evt)
        assert evt.budget_utilization_pct is None

    def test_no_division_by_zero_when_budget_is_zero(self) -> None:
        evt = _make_event(context_bytes_loaded=100, context_budget_bytes=0)
        _sink().emit(evt)
        assert evt.budget_utilization_pct is None


# ---------------------------------------------------------------------------
# _enrich_economy — tokens_total auto-computation
# ---------------------------------------------------------------------------


class TestEnrichTokensTotal:
    def test_computes_tokens_total(self) -> None:
        evt = _make_event(tokens_input=1000, tokens_output=500)
        _sink().emit(evt)
        assert evt.tokens_total == 1500

    def test_does_not_overwrite_explicit_tokens_total(self) -> None:
        evt = _make_event(tokens_input=1000, tokens_output=500, tokens_total=9999)
        _sink().emit(evt)
        assert evt.tokens_total == 9999

    def test_no_computation_when_tokens_input_missing(self) -> None:
        evt = _make_event(tokens_output=500)
        _sink().emit(evt)
        assert evt.tokens_total is None

    def test_no_computation_when_tokens_output_missing(self) -> None:
        evt = _make_event(tokens_input=1000)
        _sink().emit(evt)
        assert evt.tokens_total is None


# ---------------------------------------------------------------------------
# Zone event auto-emission
# ---------------------------------------------------------------------------


class TestZoneEventEmission:
    def test_green_zone_no_zone_event(self) -> None:
        """0–70% utilization → no zone event emitted."""
        loaded = int(40 * 1024 * 0.5)  # 50%
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        events = sink.list_events()
        zone_events = [
            e for e in events if e.event in (ECONOMY_BUDGET_WARN, ECONOMY_BUDGET_BREACH)
        ]
        assert zone_events == []

    def test_yellow_zone_no_warn_emitted(self) -> None:
        """71–90% utilization → YELLOW zone → no warn event (only compression obligation)."""
        loaded = int(40 * 1024 * 0.80)  # 80% — YELLOW zone
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        events = sink.list_events()
        warn_events = [e for e in events if e.event == ECONOMY_BUDGET_WARN]
        assert warn_events == []

    def test_red_zone_emits_warn(self) -> None:
        """91–99% utilization → RED zone → economy.budget.warn emitted."""
        loaded = int(40 * 1024 * 0.95)  # 95%
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        warn_events = [e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN]
        assert len(warn_events) == 1

    def test_breach_zone_emits_breach_not_warn(self) -> None:
        """≥100% utilization → economy.budget.breach (not warn)."""
        loaded = 40 * 1024 * 2  # 200% — definitely breached
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        events = sink.list_events()
        breach_events = [e for e in events if e.event == ECONOMY_BUDGET_BREACH]
        warn_events = [e for e in events if e.event == ECONOMY_BUDGET_WARN]
        assert len(breach_events) == 1
        assert warn_events == []

    def test_zone_event_carries_utilization_pct(self) -> None:
        loaded = int(40 * 1024 * 0.95)  # 95% — RED zone
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        warn = next(e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN)
        assert warn.budget_utilization_pct is not None
        assert warn.budget_utilization_pct > _ZONE_RED_PCT

    def test_zone_event_carries_source_event_in_details(self) -> None:
        loaded = int(40 * 1024 * 0.95)  # 95% — RED zone
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        warn = next(e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN)
        assert warn.details.get("source_event") == "runtime.session.start"

    def test_zone_event_inherits_trace_id(self) -> None:
        loaded = int(40 * 1024 * 0.95)  # 95% — RED zone
        evt = _make_event(path_id="A", context_bytes_loaded=loaded)
        sink = _sink()
        sink.emit(evt)
        warn = next(e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN)
        assert warn.trace_id == "trace-economy-test"

    def test_no_zone_event_when_utilization_not_computable(self) -> None:
        """No bytes info → no zone event."""
        evt = _make_event()
        sink = _sink()
        sink.emit(evt)
        zone_events = [
            e
            for e in sink.list_events()
            if e.event in (ECONOMY_BUDGET_WARN, ECONOMY_BUDGET_BREACH)
        ]
        assert zone_events == []

    def test_emitting_warn_event_directly_does_not_recurse(self) -> None:
        """Emitting a zone event must not trigger another zone event."""
        warn_evt = RuntimeEvent(
            event=ECONOMY_BUDGET_WARN,
            command="test",
            status="warn",
            trace_id="trace-x",
            budget_utilization_pct=85.0,
        )
        sink = _sink()
        sink.emit(warn_evt)
        all_events = sink.list_events()
        zone_events = [
            e
            for e in all_events
            if e.event in (ECONOMY_BUDGET_WARN, ECONOMY_BUDGET_BREACH)
        ]
        # Only the original warn event — no recursive emission
        assert len(zone_events) == 1

    def test_emitting_breach_event_directly_does_not_recurse(self) -> None:
        breach_evt = RuntimeEvent(
            event=ECONOMY_BUDGET_BREACH,
            command="test",
            status="warn",
            trace_id="trace-x",
            budget_utilization_pct=110.0,
        )
        sink = _sink()
        sink.emit(breach_evt)
        zone_events = [
            e
            for e in sink.list_events()
            if e.event in (ECONOMY_BUDGET_WARN, ECONOMY_BUDGET_BREACH)
        ]
        assert len(zone_events) == 1

    def test_exactly_at_yellow_boundary_no_zone_event(self) -> None:
        """Exactly 70.0% → GREEN (not > 70.0) → no zone event."""
        budget = 1000
        loaded = 700  # exactly 70.0%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        sink = _sink()
        sink.emit(evt)
        zone_events = [
            e
            for e in sink.list_events()
            if e.event in (ECONOMY_BUDGET_WARN, ECONOMY_BUDGET_BREACH)
        ]
        assert zone_events == []

    def test_just_above_yellow_boundary_no_warn(self) -> None:
        """70.1% → YELLOW zone → no warn event (compression obligation, not warn)."""
        budget = 1000
        loaded = 701  # 70.1%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        sink = _sink()
        sink.emit(evt)
        warn_events = [e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN]
        assert warn_events == []

    def test_just_above_red_boundary_emits_warn(self) -> None:
        """90.1% → RED zone → economy.budget.warn emitted."""
        budget = 1000
        loaded = 901  # 90.1%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        sink = _sink()
        sink.emit(evt)
        warn_events = [e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN]
        assert len(warn_events) == 1

    def test_exactly_at_red_boundary_no_warn(self) -> None:
        """Exactly 90.0% → still YELLOW (not > 90.0) → no warn event."""
        budget = 1000
        loaded = 900  # exactly 90.0%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        sink = _sink()
        sink.emit(evt)
        warn_events = [e for e in sink.list_events() if e.event == ECONOMY_BUDGET_WARN]
        assert warn_events == []

    def test_exactly_at_breach_boundary_emits_breach(self) -> None:
        """Exactly 100.0% → BREACH."""
        budget = 1000
        loaded = 1000  # 100.0%
        evt = _make_event(context_bytes_loaded=loaded, context_budget_bytes=budget)
        sink = _sink()
        sink.emit(evt)
        breach_events = [
            e for e in sink.list_events() if e.event == ECONOMY_BUDGET_BREACH
        ]
        assert len(breach_events) == 1
