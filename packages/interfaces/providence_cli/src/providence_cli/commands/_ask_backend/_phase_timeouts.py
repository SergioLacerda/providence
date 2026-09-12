"""Default per-phase watchdog thresholds for `providence ask` (design.md 3, T-04).

Values are derived from real, locally observed data rather than guessed:

- `ask.budget.guard`, `ask.workspace.resolve`, `ask.organize.intake`,
  `ask.handshake.guard`, `ask.profile.resolve`  sampled at 0-2ms from
  real `governance.ask.phase` events in this workspace's own
  `.providence/runtime/compliance-events.jsonl` (62 prior `providence ask` invocations,
  372 phase events). Given a 100ms threshold (~50-100x observed median).
- `ask.governance.snapshot`  the dominant phase, sampled at ~9-20ms with a
  warm cache in the same JSONL sample. No cold-cache-miss (disk reload +
  signature verification) sample was available locally, so the threshold
  carries a wider margin (2000ms, ~100x the warm-cache median) rather than
  a tight bound, to avoid false-positive warnings on a legitimate cold
  cache.
- `ask.runtime.handbook`  newly split out of what was previously folded
  into `ask.governance.snapshot`'s timing; no isolated sample exists yet,
  so it inherits a proportionally generous threshold (300ms).
- `ask.cli.entry`, `ask.response.render`, `ask.telemetry.emit`  new
  phases with no prior samples (they did not exist before this mission);
  thresholds are set as a generous multiple of what similarly
  lightweight, non-I/O phases measure above, not a tight bound.
- `ask.external.llm_exchange`  deliberately excluded from the tight
  defaults: this phase measures adapter-reported LLM inference latency,
  which is expected to legitimately take seconds. A low threshold here
  would produce constant false-positive "slow" warnings for normal LLM
  latency, defeating the diagnostic purpose of the watchdog.

`tests/perf/benchmark_ask_cold_invocation.py`'s existing benchmark
(`tests/perf/benchmark_ask_cold_invocation_results.json`) measures only
whole-process wall time (subprocess start + interpreter import + full call,
p50 ~479-494ms, p95 ~502-649ms as of 2026-07-30), not per-phase timing, so
it could not directly seed these per-phase values  the JSONL sample above
is the only available per-phase source.

These are starting defaults, not hard-coded policy: overriding
`thresholds_ms/default_threshold_ms` on a `PhaseTimer` instance replaces
them per call site.
"""

from __future__ import annotations

DEFAULT_ASK_PHASE_TIMEOUTS_MS: dict[str, int] = {
    "ask.cli.entry": 100,
    "ask.budget.guard": 100,
    "ask.workspace.resolve": 100,
    "ask.organize.intake": 500,
    "ask.handshake.guard": 100,
    "ask.profile.resolve": 100,
    "ask.runtime.handbook": 300,
    "ask.governance.snapshot": 2000,
    "ask.response.render": 500,
    "ask.telemetry.emit": 500,
    "ask.external.llm_exchange": 60_000,
}

# Applied to any phase not listed above (there should be none today, but
# this keeps future phases from silently bypassing the watchdog).
DEFAULT_ASK_TIMEOUT_MS = 1000
