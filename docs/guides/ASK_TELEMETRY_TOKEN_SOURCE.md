# `providence ask` Telemetry: Token Source and LLM Latency Semantics

Context for operators reading `governance.ask` / `governance.ask.phase` telemetry
events (see `docs/plans/2026-07-09-sdd-ask-traceroute.md` for the full
trace-route design).

## `token_source` values

The `governance.ask` event's `details.token_source` field (populated by
`packages/interfaces/providence_cli/src/providence_cli/services/ask_telemetry.py::resolve_tokens`)
can be one of:

- `env` — token counts were supplied via environment variables
  (`SDD_TOKENS_INPUT`/`SDD_TOKENS_OUTPUT`), i.e. CLI- or
  environment-provided values, not measured by `providence_cli` itself.
- `estimated` — token counts were derived from a local heuristic estimate
  (`len(text) // 4`, a byte-based approximation of the query and output text).
- `unknown` — resolution itself failed (see
  `services/ask_telemetry.py::resolve_tokens`'s exception fallback); treat as
  no reliable token count being available at all.

There is currently **no `actual`/API-metered token source** wired into `providence
ask` telemetry — no code path in this repository calls an LLM billing/usage
API to obtain ground-truth token counts. Do not assume or report one exists
until such an integration is added.

## Token counts are not latency evidence

A `token_source` of `env` or `estimated` says nothing about how long any
downstream LLM/API exchange took. In particular:

- Do not infer `ask.external.llm_exchange` duration from token counts.
- The `ask.external.llm_exchange` phase event (see the trace-route plan,
  Task 4) is only emitted when `SDD_ADAPTER_LLM_EXCHANGE_MS` is explicitly
  set by an adapter/IDE integration, with
  `details.measurement_quality == "adapter_reported"`. When that phase is
  absent from a `governance.ask.phase` trace, it means the exchange was not
  observed — not that it took `0ms`.
- If you need to correlate token volume with latency, join on `trace_id`
  across the parent `governance.ask` event's `tokens_input`/`tokens_output`
  fields and the `ask.external.llm_exchange` phase's `duration_ms`
  separately; do not conflate the two into a single derived metric without
  making the join explicit.
