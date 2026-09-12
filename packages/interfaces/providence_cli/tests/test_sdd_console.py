"""Tests for the shared `[SDD] ...` console line formatting helpers."""

from __future__ import annotations

from providence_cli.utils.providence_console import (
    format_sdd_line,
    format_sdd_phase_line,
)


def test_format_sdd_line_uses_prefix():
    assert format_sdd_line("Workspace initialized") == "[SDD] Workspace initialized"


def test_format_sdd_phase_line_formats_seconds_with_two_decimals():
    line = format_sdd_phase_line("ask.governance.snapshot", 1310)
    assert line.startswith("[SDD] ask.governance.snapshot")
    assert line.endswith("1.31s")


def test_format_sdd_phase_line_rounds_sub_millisecond_durations():
    line = format_sdd_phase_line("ask.cli.entry", 20)
    assert line.endswith("0.02s")


def test_format_sdd_phase_line_pads_short_labels_for_alignment():
    short = format_sdd_phase_line("Total", 1710)
    long = format_sdd_phase_line("ask.governance.snapshot", 1710)
    # Both duration columns start at the same offset from "[SDD] ".
    short_duration_start = short.index("1.71s")
    long_duration_start = long.index("1.71s")
    assert short_duration_start == long_duration_start
