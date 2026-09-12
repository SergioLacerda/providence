# 🧠 CORE MANDATES — Runtime Contract

## 🎯 Purpose

Define mandatory behavioral contracts that ALL agents MUST follow.

---

## 🧬 Mandate Model

## Mandate Registry

| ID   | Title                          | File                          |
|------|--------------------------------|-------------------------------|
| M003 | Context Awareness & Task Caching | [M003_CONTEXT_AWARENESS.md](M003_CONTEXT_AWARENESS.md) |
| M005 | Token Economy Enforcement      | [M005_TOKEN_ECONOMY.md](M005_TOKEN_ECONOMY.md) |
| M007 | Telemetry Enforcement          | [M007_TELEMETRY.md](M007_TELEMETRY.md) |
| M008 | Audit Integrity                | [M008_AUDIT_INTEGRITY.md](M008_AUDIT_INTEGRITY.md) |
| M009 | OpenTelemetry Compliance       | [M009_OTEL_COMPLIANCE.md](M009_OTEL_COMPLIANCE.md) |
| M010 | Delivery Hygiene Enforcement   | [M010_DELIVERY_HYGIENE.md](M010_DELIVERY_HYGIENE.md) |
| M011 | English Language Standard      | [M011_LANGUAGE_STANDARD_ENGLISH.md](M011_LANGUAGE_STANDARD_ENGLISH.md) |
| M015 | Bidirectional Agent Handshake  | [M015_BIDIRECTIONAL_HANDSHAKE.md](M015_BIDIRECTIONAL_HANDSHAKE.md) |
| M016 | Guardrail Non-Regression       | [M016_GUARDRAIL_IMMUTABILITY.md](M016_GUARDRAIL_IMMUTABILITY.md) |
| M017 | Analysis Plugin Compliance     | [M017_ANALYSIS_PLUGIN_COMPLIANCE.md](M017_ANALYSIS_PLUGIN_COMPLIANCE.md) |
| M018 | Code Quality Baseline          | [M018_CODE_QUALITY_BASELINE.md](M018_CODE_QUALITY_BASELINE.md) |
| M019 | Governance Federation          | [M019_GOVERNANCE_FEDERATION.md](M019_GOVERNANCE_FEDERATION.md) |
| M020 | Governed Compact Logging       | [M020_GOVERNED_COMPACT_LOGGING.md](M020_GOVERNED_COMPACT_LOGGING.md) |

Not every canonical mandate is listed above — this index covers mandates
whose canonical document lives directly under `core/mandates/`. Three
mandates are documented elsewhere on purpose and are intentionally omitted
here rather than silently missing:

| ID   | Title                          | Canonical location |
|------|--------------------------------|---------------------|
| M001 | Clean Architecture             | [../../features/CLEAN_ARCHITECTURE.md](../../features/CLEAN_ARCHITECTURE.md) (selectable feature) |
| M002 | Test-Driven Development (TDD)  | [../../features/TDD.md](../../features/TDD.md) (selectable feature) |
| M006 | RFC Process for Breaking Changes | [../../guides/M006_RFC_PROCESS.md](../../guides/M006_RFC_PROCESS.md) |

The full active mandate set is the union of this table and the one above —
see `.providence/source/mandates/mandates.md` for the canonical, generated register.

---

## Mandate Model

Each mandate is defined as an operational unit:

```json
{
  "id": "MXXX",
  "name": "string",
  "type": "MANDATE",
  "enforcement": "HARD",
  "required": true,
  "phase": ["pre-execution", "execution", "post-execution"],
  "actions": [],
  "validation": [],
  "failure_mode": "DEGRADED | BLOCKED"
}
