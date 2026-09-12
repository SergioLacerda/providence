# Observability Contract (MVP)

## Purpose

Define the minimum production contract that correlates runtime events, metrics summaries, and trace-compatible attributes.

## Correlation Keys

All governed command telemetry should support correlation using:

- `trace_id`
- `event`
- `command`
- `profile`
- `start_ts` / `timestamp`

## Signal Surfaces

1. Runtime events (`.providence/runtime/compliance-events.jsonl` or configured sink)
2. Metrics summary path (`sdd metrics summary`)
3. Trace-compatible attribute mapping (`providence_telemetry.to_otel_attributes`)

## Operator Query Path (MVP)

1. Identify failing command and `trace_id` in runtime/compliance logs.
2. Cross-check event status via `sdd metrics summary`.
3. Normalize event attributes for tracing/export pipeline using `to_otel_attributes`.

## Verification Gate

The CI gate `tools/ci/check_observability_contract.py` validates:

- this contract file exists;
- required correlation keys and surfaces are declared;
- operator query path section is present.
