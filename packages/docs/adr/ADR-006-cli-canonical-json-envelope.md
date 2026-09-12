# ADR-006 — CLI Canonical JSON Envelope (Big-Bang Cut)

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The `providence_cli` package accumulated a dual-payload pattern during an envelope migration:
every JSON response emitted both a canonical envelope (`status`, `command`, `ok`, `error`, `data`)
and a mirrored legacy payload at the top level. A `SDD_CLI_ENVELOPE_STRICT` flag controlled
which shape consumers received.

This transition layer had no planned end date, created two code paths to maintain, and made
integration tests ambiguous about which shape was authoritative.

---

## Decision

**All CLI JSON responses use exactly one envelope shape. No compatibility layer.**

```json
{
  "status": "ok|error",
  "command": "<canonical-command-id>",
  "ok": true,
  "error": null,
  "data": {}
}
```

Rules:

1. `data` is the only payload location — no fields mirrored at the top level.
2. Error cases use the same envelope with a structured `error` object and `"ok": false`.
3. `SDD_CLI_ENVELOPE_STRICT` and all legacy mirroring logic are removed — no flag, no shim.
4. Interactive plain-text output (non-JSON mode) is unaffected.

The cut was executed as a single atomic branch: all commands, shared contracts, tests, and
snapshots updated in one pass before merge.

---

## Rationale

- **Gradual migration rejected:** compatibility shims require maintaining two code paths
  indefinitely, and tests can pass against the wrong shape silently.
- **Feature-flag rejected:** no planned graduation date means the flag becomes permanent
  infrastructure with no owner.
- **Big-bang accepted:** atomic execution is higher risk per-commit but guarantees the
  codebase is never in an ambiguous state post-merge.

---

## Consequences

- Consumers of `providence_cli` JSON output that read top-level payload fields break immediately;
  they must migrate to `data.<field>`.
- `build_ok_result` and `build_error_result` are the only allowed builders — ad-hoc
  `json.dumps({...})` in command handlers is a policy violation.
- New commands are correct by construction: copy an existing command handler and the shape
  is guaranteed.

---

## Links

- Implementation: `packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`
- Related: ADR-001 (Runtime Authority Boundary)
