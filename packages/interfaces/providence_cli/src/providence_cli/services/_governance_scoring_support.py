"""Support helpers for governance scoring output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table


def render_score_breakdown(
    *,
    checks: list[tuple[str, bool, int]],
    final_score: int,
    threshold: int,
    verbose: bool,
    console: Console,
) -> None:
    if verbose:
        table = Table(
            title="Governance Score Breakdown", show_header=True, header_style="bold"
        )
        table.add_column("Check", style="cyan")
        table.add_column("Weight", style="yellow")
        table.add_column("Status", style="green")
        for label, passed, weight in checks:
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(label, str(weight), status)
        console.print(table)
    color = "green" if final_score >= threshold else "red"
    console.print(
        f"[{color}]Governance score: {final_score}/100 (threshold: {threshold})[/{color}]"
    )


def render_adherence_breakdown(
    *,
    result: dict[str, Any],
    threshold: int,
    window: int,
    verbose: bool,
    console: Console,
) -> int:
    score = int(result["score"])
    details = result["details"]
    if verbose:
        table = Table(
            title="Governance Adherence Breakdown",
            show_header=True,
            header_style="bold",
        )
        table.add_column("Dimension", style="cyan")
        table.add_column("Max", style="yellow", justify="right")
        table.add_column("Score", style="green", justify="right")
        table.add_column("Detail")
        table.add_row(
            "Behavioral",
            "50",
            str(details["behavioral_score"]),
            f"allows={details['allows']} warns={details['warns']} blocks={details['blocks']} (last {window}h)",
        )
        table.add_row(
            "Structural",
            "30",
            str(details["structural_score"]),
            details["structural_status"],
        )
        table.add_row(
            "Freshness",
            "20",
            str(details["freshness_score"]),
            details["freshness_status"],
        )
        console.print(table)
    color = "green" if score >= threshold else "red"
    console.print(
        f"[{color}]Governance adherence: {score}/100 (threshold: {threshold})[/{color}]"
    )
    return score


def resolve_profile_check(
    *, ws_root: Path, resolve_profile_fn: Any, workspace_error_cls: type[Exception]
) -> tuple[list[tuple[str, bool, int]], Any]:
    try:
        profile_ctx = resolve_profile_fn(root=ws_root)
        return [(".providence/profile valid", True, 30)], profile_ctx
    except workspace_error_cls:
        return [(".providence/profile valid", False, 30)], None


def artifact_candidates(*, ws_root: Path, compiled_active_dir_fn: Any) -> list[Path]:
    return [compiled_active_dir_fn(ws_root) / "governance-core.json"]


def ahp_check(
    *, ws_root: Path, handshake_cls: Any
) -> tuple[tuple[str, bool, int], Any]:
    ahp = handshake_cls(project_root=ws_root)
    _, report = ahp.validate(output_mode="silent", force_recheck=True)
    confidence_ok = report.confidence >= 50.0
    return (
        f"AHP confidence >= 50% (actual: {report.confidence:.1f}%)",
        confidence_ok,
        20,
    ), report


def core_hash_matches(*, profile_ctx: Any, candidates: list[Path]) -> bool:
    if (
        profile_ctx is None
        or not profile_ctx.core_hash
        or not any(p.exists() for p in candidates)
    ):
        return False
    try:
        import hashlib
        import json as _json

        art_path = next(path for path in candidates if path.exists())
        data = _json.loads(art_path.read_bytes())
        artifact_fp = str(data.get("fingerprint", "")).strip()
        if artifact_fp:
            return bool(artifact_fp[:16] == profile_ctx.core_hash)
        clean = {
            key: value
            for key, value in data.items()
            if key not in {"_signature", "fingerprint"}
        }
        computed = hashlib.sha256(
            _json.dumps(clean, sort_keys=True).encode()
        ).hexdigest()[:16]
        return bool(computed == profile_ctx.core_hash)
    except Exception:
        return False
