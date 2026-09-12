# 📏 Onboarding Metrics — Canonical KPI Definitions

## 🎯 Purpose

Define the normative KPI names, measurement points, and violation signals for governance
onboarding observability. Field names in this document are **authoritative** — tooling MUST
match exactly.

---

## 🔒 Contract Rule

> Any signal that measures onboarding completeness or governance-session health
> MUST use the KPI names defined in this document.

---

## 📐 Onboarding KPIs

| KPI | Definition | Threshold | Violation Signal |
|-----|-----------|-----------|-----------------|
| `governance.session.handshake_active` | Session has an active handshake (`providence runtime status` returns `drift=none`) | `true` | Handshake absent → degraded governance; run `providence governance handshake --init` |
| `governance.onboarding.bootstrap_complete` | `.providence/agent-instructions.md` was read in the current session bootstrap | `true` | Agent operating without governance context → stale or wrong behavior |
| `governance.drift.profile_mismatch_count` | Count of profile-mismatch drift events emitted in the current session | `0` | Any value > 0 → profile enforcement failure; check `providence runtime status` |
| `governance.session.first_ask_latency_ms` | Time (ms) from session start to first successful `providence ask` invocation | Informative | No hard threshold; use as baseline for regression detection |

---

## 📊 Measurement Points

| KPI | Where measured |
|-----|---------------|
| `governance.session.handshake_active` | `providence runtime status` → `drift` field |
| `governance.onboarding.bootstrap_complete` | Agent bootstrap log / session telemetry |
| `governance.drift.profile_mismatch_count` | `RuntimeEvent` stream; event type `governance.drift.profile_mismatch` |
| `governance.session.first_ask_latency_ms` | Telemetry sink; field `duration_ms` on first `governance.ask` event |

---

## References

- Economy KPIs: [`economy/metrics.md`](../economy/metrics.md)
- Context Awareness Mandate: `docs/spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md`
- Telemetry fields: [`telemetry/INDEX.md`](../telemetry/INDEX.md)
