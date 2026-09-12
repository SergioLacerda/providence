"""Tests for the M020 canonical event routing guard in `ask_telemetry`."""

from __future__ import annotations

import json

import pytest

from providence_cli.services.ask_telemetry import route_canonical_event
from providence_core.output.canonical_event import CanonicalLogEvent, ProfileRenderer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("level", ["debug", "trace"])
def test_debug_and_trace_events_emit_json_and_skip_profile_rendering(
    level: str,
) -> None:
    event = CanonicalLogEvent(
        level=level,
        phase="ask",
        event_type="context_loaded",
        summary="loaded compiled governance context",
        decision="proceed",
        artifact_path=".providence/runtime/governance-state.json",
    )

    rendered = route_canonical_event(event, renderer=ProfileRenderer(profile="epic"))

    assert json.loads(rendered) == event.to_telemetry_dict()
    assert rendered != event.simple_output()


@pytest.mark.parametrize("level", ["info", "warn", "error"])
def test_non_telemetry_levels_use_profile_renderer(level: str) -> None:
    event = CanonicalLogEvent(
        level=level,
        phase="ask",
        event_type="context_loaded",
        summary="loaded compiled governance context",
    )

    rendered = route_canonical_event(event)

    assert rendered == event.simple_output()
