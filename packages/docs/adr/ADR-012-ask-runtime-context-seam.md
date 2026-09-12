# ADR-012 — AskRuntimeContext: Dependency-Injection Seam for `providence ask` Testing

**Status:** Accepted
**Date:** 2026-06-10
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

`packages/interfaces/providence_cli/src/providence_cli/commands/_ask_backend.py` is the only
source file in `providence_cli` still over the Wave 8 ≤300-line gate (1060 lines after
the `_emit_ask_json_response`/`_emit_ask_text_response`/`_build_json_dossier_lines`
extraction into `services/ask_response.py`). Its test suite relies on ~121
`unittest.mock.patch("providence_cli.commands._ask_backend.<symbol>")` call sites
across 9 files (8 in `providence_cli/tests/`, plus `providence_core/tests/cli/test_ask_command.py`
and `test_ask_security.py`), targeting 15-22 distinct symbols
(`_resolve_workspace_root`, `_get_profile_state`, `_emit_ask_telemetry`,
`_run_organize_intake`, `build_governed_ask_snapshot`, `_guard_budget_breach`,
`_guard_handshake`, `_build_dossier_lines`, `_load_dossier_artifact`,
`run_sdd_organize`, `_runtime_drift_check`, `_should_use_organize`,
`_resolve_tokens`, `OtelBridge`, `OtlpHttpExporter`, `TelemetrySink`, etc.).

`unittest.mock.patch("module.X", ...)` rewrites `X` in the *caller's* global
namespace at call time. This means every one of these ~121 patches assumes the
patched symbol's *call site* remains a global lookup inside
`providence_cli.commands._ask_backend`. Moving an orchestration helper's call site to
another module — even when the symbol's definition is re-exported by name —
breaks the patch for that call site, because the moved code resolves the name
in its new module's namespace instead.

This is the structural reason `_ask_backend.py`'s decomposition is blocked: the
"extract + re-export" pattern used successfully for every other Wave 8 file
(`commands/skills.py`, `commands/telemetry.py`, `commands/metrics.py`, etc.)
does not work here, because in those files the *callers* of the moved helpers
stayed put — here, the orchestration chain itself (`_ask_cmd_impl` and its
~12 helpers) is what needs to shrink.

---

## Decision

Introduce a small `AskRuntimeContext` object that bundles the currently
module-global-patched collaborators as explicit fields/callables, and have
`_ask_cmd_impl` (and the orchestration helpers it calls) accept this context
as an explicit parameter instead of doing bare module-global lookups.

- Tests construct an `AskRuntimeContext` with fakes/stubs for the collaborators
  under test, instead of `mock.patch`-ing `providence_cli.commands._ask_backend.<name>`.
- A default-wired `AskRuntimeContext` (using the real implementations) is
  constructed by `_ask_cli_cmd`/`ask_cmd` for production use, so the public CLI
  behavior is unchanged.
- Existing thin module-level wrappers (`_resolve_workspace_root`,
  `_emit_ask_telemetry`, etc.) and `_ask_backend.__all__` re-exports remain in
  place during migration, so any consumer still patching `_ask_backend.<name>`
  continues to work — this is an additive seam, not a flag-day rewrite.
- Once the context exists, orchestration helpers can be moved into
  `services/ask_*` modules without breaking tests, because the seam no longer
  depends on the physical module location of the call site — it depends on the
  context object passed in.

This decision authorizes the seam as the target architecture for `_ask_backend.py`.
Implementation (the symbol enumeration/grouping and the incremental
test-file-by-test-file migration) is scoped as its own follow-up
discovery + refinement mission, executed before or alongside the remaining
`_ask_backend.py` decomposition work.

---

## Consequences

- **Unblocks `_ask_backend.py` decomposition.** The remaining incremental
  "seam first" decomposition (grouped by test file, full-suite-green per
  group) becomes safe to execute without the risk of silently-unpatched call
  sites.
- **Two testing styles coexist during migration**: `mock.patch` on
  `_ask_backend.<name>` (legacy, still works via re-exports) and
  `AskRuntimeContext` construction (new). This is intentional — it allows
  test-file-by-test-file migration, but adds short-term cognitive overhead
  (two ways to stub the same collaborator).
- **New public-ish type** (`AskRuntimeContext`) added to `providence_cli`'s internal
  surface. Cross-package impact: `providence_core/tests/cli/test_ask_command.py` and
  `test_ask_security.py` (a security-relevant suite) patch `_ask_backend`
  symbols and would eventually migrate too — this raises the review bar per
  CLAUDE.md security guidance.
- **Requires an enumeration pass** before implementation: all 15-22 patched
  symbols need to be grouped into coherent context fields (telemetry,
  workspace/governance resolution, dossier building, organize delegation,
  token capture, drift/handshake guards). This enumeration is itself
  non-trivial and is the first task of the follow-up mission, not assumed
  here.

---

## Alternatives Considered

- **Do nothing (keep `mock.patch` as-is).** Rejected — leaves
  `_ask_backend.py` permanently over the ≤300L gate and the brittleness
  compounds with every future change to the file.
- **Full rewrite of `_ask_backend.py` + its ~121 test assertions.** Rejected:
  cost asymmetry (no incremental checkpoints), coverage-provenance risk
  (years of accumulated edge-case knowledge encoded in existing patches), and
  `providence ask` is a security-relevant, cross-package surface
  (`test_ask_security.py`) — raising the bar against a from-scratch rewrite.
- **Pure "extract + re-export" without a context object** (the pattern used
  for every other Wave 8 file). Works only up to the point where a helper's
  *caller* also needs to move; for `_ask_backend.py` the caller chain
  (`_ask_cmd_impl` and friends) is exactly what needs to shrink, so this
  alternative does not solve the core problem — every future move would
  repeat the same brittleness.

---

## Links

- `.analysis/pending/2026-06-10-ask-backend-decomposition-discovery.md` (origin of this decision)
- `packages/interfaces/providence_cli/REFACTOR_NOTES.md` (Wave 1 / Wave 8 — `_ask_backend.py` blocker history)
