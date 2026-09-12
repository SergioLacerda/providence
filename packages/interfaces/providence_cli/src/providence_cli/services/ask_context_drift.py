"""Workspace context drift checks and last-ask fingerprint cache for `providence ask`.

Split out of `ask_context.py` (T8,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from providence_cli.services.ask_governance_state_cache import (
    _load_governance_state,
    _store_governance_state,
)

logger = logging.getLogger(__name__)


def check_root_seed_drift(workspace_root: Path) -> bool:
    """Return True if any root seed file's fingerprint header disagrees with metadata.json.

    Structurally distinct from `check_fingerprint_drift` below: this compares
    installed root files (AGENTS.md, CLAUDE.md, GEMINI.md) against source
    metadata, not cached runtime state against the currently loaded fingerprint.
    Intentionally not merged with `check_fingerprint_drift`  see
    `governance_config_reader.check_root_seed_drift` for the underlying check.
    """
    from providence_cli.services.governance_config_reader import (
        check_root_seed_drift as _check_root_seed_drift_impl,
    )

    ok, _reason = _check_root_seed_drift_impl(str(workspace_root / ".providence"))
    return not ok


def resolve_fingerprint_drift_status(
    workspace_root: Path, loaded_fingerprint: str
) -> str:
    """Return one of "clean", "drifted", "unverifiable", or "error".

    Unifies what used to be a bare `bool` (see DRF-01,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`) so a
    caller can tell "compared and found aligned" apart from "had nothing
    comparable to compare against"  both previously collapsed to `False`,
    which a consumer could misread as a proven absence of drift.

    Only ``last_ask.compiled_fingerprint_used`` is ever compared against
    ``loaded_fingerprint``  both are compiled-artifact hashes, the same
    domain. Falling back to ``spec_fingerprint`` (a hash of *source* files)
    was DRF-02: comparing hashes from two different domains produces a
    permanent false positive whenever they diverge for reasons unrelated to
    actual drift. Absence of a same-domain reference is now reported as
    "unverifiable", never silently compared anyway.
    """
    if not loaded_fingerprint:
        return "unverifiable"
    try:
        data = _load_governance_state(workspace_root)
        if not data:
            return "unverifiable"
        last_ask = data.get("last_ask") or {}
        cached_fp = str(last_ask.get("compiled_fingerprint_used", "")).strip()
        if not cached_fp:
            return "unverifiable"
        return "drifted" if loaded_fingerprint[:8] != cached_fp[:8] else "clean"
    except Exception:
        return "error"


def check_fingerprint_drift(workspace_root: Path, loaded_fingerprint: str) -> bool:
    """Return True only when a same-domain comparison found actual drift.

    Thin boolean projection of `resolve_fingerprint_drift_status` kept for
    the many existing callers that gate on a plain bool (telemetry payloads,
    JSON output schema, renderer text)  "unverifiable" and "error" both
    project to `False`, matching this function's pre-existing contract.
    Prefer `resolve_fingerprint_drift_status` in new code that needs to
    distinguish "confirmed clean" from "nothing to compare against".
    """
    return (
        resolve_fingerprint_drift_status(workspace_root, loaded_fingerprint)
        == "drifted"
    )


def write_runtime_cache(workspace_root: Path, last_ask: dict[str, Any]) -> None:
    """Persist last-ask metadata to the runtime governance-state cache."""
    try:
        data = _load_governance_state(workspace_root)
        data["last_ask"] = last_ask
        _store_governance_state(workspace_root, data, changed_keys={"last_ask"})
    except Exception as exc:
        logger.debug("Failed to update runtime cache: %s", exc)


def _read_runtime_state(workspace_root: Path) -> dict[str, Any]:
    return _load_governance_state(workspace_root)


def compute_routing_signature(query: str, skill: str | None, fingerprint: str) -> str:
    """Return a stable signature for a routing-decision cache lookup.

    Combines normalized query text, skill selection, and the compiled
    governance fingerprint. The fingerprint alone already reflects the
    combined mandates/registry state (`.providence/metadata.json` ->
    `fingerprints.combined`), so no separate registry-version component is
    needed for invalidation.

    Fingerprint domain (SEC-08,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
    purpose=cache-lookup key (NOT a cryptographic signature despite the
    name), algorithm=sha256, normalization=lowercased/whitespace-collapsed
    query + lowercased skill + the caller-supplied fingerprint string
    joined with `|`, length=16-char truncated hex. Do not compare this
    value against a different domain's hash (e.g.
    `GovernanceFingerprinter.generate`'s full 64-char integrity digest, or
    `HandshakeCache.compute_spec_fingerprint`'s 16-char governance-version
    fingerprint)  same length is not the same domain. See DRF-02 for a
    concrete historical instance of exactly that mistake.
    """
    normalized_query = " ".join(query.strip().lower().split())
    normalized_skill = (skill or "").strip().lower()
    raw = f"{normalized_query}|{normalized_skill}|{fingerprint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_last_known_fingerprint(workspace_root: Path) -> str:
    """Return the compiled fingerprint recorded by the previous `providence ask` call, if any."""
    last_ask = _read_runtime_state(workspace_root).get("last_ask") or {}
    return str(last_ask.get("compiled_fingerprint_used", "")).strip()
