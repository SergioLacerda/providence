"""Governance score and adherence gates for `providence doctor run`."""

from __future__ import annotations

import logging

import typer

from providence_cli.utils.providence_authority import (
    compiled_active_dir,
    enforce_path_policy,
    resolve_workspace_root,
)

logger = logging.getLogger(__name__)


def _apply_score_gate(score_threshold: int) -> None:
    """D4: governance score gate. Raises typer.Exit(1) if score is below threshold."""
    if score_threshold <= 0:
        return
    try:
        from providence_core.governance.handshake import AgentHandshakeProtocol
        from providence_core.utils.environment import (
            WorkspaceNotInitializedError,
            resolve_profile,
        )

        ws_root = resolve_workspace_root()
        ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
        if ws_root is None:
            return

        artifact_candidates = [compiled_active_dir(ws_root) / "governance-core.json"]
        ahp = AgentHandshakeProtocol(project_root=ws_root)
        _, ahp_report = ahp.validate(output_mode="silent")
        profile_ctx = None
        profile_ok = True
        try:
            profile_ctx = resolve_profile(root=ws_root)
        except WorkspaceNotInitializedError:
            profile_ok = False

        artifacts_ok = any(p.exists() for p in artifact_candidates)
        confidence_ok = ahp_report.confidence >= 50.0

        # Check 4: core_hash in profile matches compiled artifact (same logic as governance.py)
        hash_ok = False
        if profile_ctx is not None and profile_ctx.core_hash and artifacts_ok:
            try:
                import hashlib
                import json as _json

                art_path = next(p for p in artifact_candidates if p.exists())
                raw = art_path.read_bytes()
                data = _json.loads(raw)
                artifact_fp = str(data.get("fingerprint", "")).strip()

                if artifact_fp:
                    hash_ok = artifact_fp[:16] == profile_ctx.core_hash
                else:
                    clean = {
                        k: v
                        for k, v in data.items()
                        if k not in {"_signature", "fingerprint"}
                    }
                    computed = hashlib.sha256(
                        _json.dumps(clean, sort_keys=True).encode()
                    ).hexdigest()[:16]
                    hash_ok = computed == profile_ctx.core_hash
            except Exception:
                hash_ok = False

        # Use centralized score computation (includes all 4 checks for consistency)
        from providence_core.governance.scoring import compute_governance_score

        checks = [
            ("profile valid", profile_ok, 30),
            ("artifacts compiled", artifacts_ok, 30),
            ("AHP confidence >= 50%", confidence_ok, 20),
            ("core_hash matches artifact", hash_ok, 20),
        ]
        score = compute_governance_score(checks)

        if score < score_threshold:
            typer.echo(
                f"[SDD] Governance score {score}/100 below threshold {score_threshold}. Run 'providence governance score --verbose' for details.",
                err=True,
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.debug("Score gate check failed unexpectedly", exc_info=True)


def _apply_adherence_gate(adherence_threshold: int) -> None:
    """D4b: governance adherence gate. Raises typer.Exit(1) if adherence is below threshold."""
    if adherence_threshold <= 0:
        return
    try:
        from providence_core.governance.compliance import compute_governance_adherence

        ws_root = resolve_workspace_root()
        adherence = compute_governance_adherence(workspace_root=ws_root)["score"]

        if adherence < adherence_threshold:
            typer.echo(
                f"[SDD] Governance adherence {adherence}/100 below threshold {adherence_threshold}. Run 'providence governance adherence --verbose' for details.",
                err=True,
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.debug("Adherence gate check failed unexpectedly", exc_info=True)
