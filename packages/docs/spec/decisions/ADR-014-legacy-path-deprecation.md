# ADR-014: Remove Legacy Path Fallbacks

- Status: Accepted
- Date: 2026-05-20

## Context

Three legacy path fallbacks existed in the codebase for backward compatibility with
workspaces predating the `.providence/` layout:

| ID | Location | Legacy path | Canonical path |
|----|----------|-------------|----------------|
| L1 | `providence_runtime/signatures.py` | `compiled/trusted-keys.json`, `compiled/audit/trusted-keys.json` | `.providence/trust/trusted-keys.json` |
| L2 | `providence_core/governance/audit.py` | `generated/master/compiled/` | `.providence/compiled/` |
| L3 | `providence_core/utils/loader.py` | `compiled/<filename>` | `compiled/audit/<filename>` |

These fallbacks were introduced to ease migration but have two failure modes:

1. **Silent degradation**: L3 returned the wrong path without any warning when the
   canonical path was absent. Callers could silently load stale or incorrect metadata.
2. **Masked misconfiguration**: L1 and L2 allowed misconfigured workspaces to continue
   operating in a degraded state instead of failing loudly and prompting migration.

## Decision

Remove all three fallbacks. Misconfigured workspaces now fail loudly:

- L1: `_resolve_keyring_path` only checks canonical + env var override; any workspace
  with only a legacy keyring path receives `(None, "none", "")`.
- L2: `_audit_signatures` emits HIGH "No compiled governance artifacts found" immediately
  when `.providence/compiled/` is absent; `generated/master/compiled/` is no longer a fallback.
- L3: `_resolve_metadata_path` always returns `compiled/audit/<filename>`; the caller
  handles `FileNotFoundError` if the file does not exist.

## Evidence of Safety

- No CI job, Makefile target, or shell script invokes the legacy paths.
- L1 deprecation warning ("will be removed in 2 releases") was present since at least
  release `eede782` (2026-05-20) with no reported issues.
- L2 LOW audit issue was already signaling migration to all affected workspaces.
- L3 silent fallback had no test coverage before this change, indicating no known caller
  depended on it.
- All existing tests pass after removal (15 signatures, 27 audit, 2 loader).

## Consequences

**Positive:**

- Misconfigured workspaces fail loudly with actionable error messages
- Codebase has no hidden state transitions based on which legacy files happen to exist
- Reduces attack surface: no alternative trust anchor paths can be silently activated

**Negative:**

- Any workspace still using a legacy layout will break with a HIGH integrity error or
  missing-file error — acceptable given the migration timeline and prior warnings
