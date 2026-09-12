"""Support helpers for governance security handlers."""

from __future__ import annotations

import contextlib
import json as _json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from providence_core.utils.compiler_runner import CompilerRunner


def resolve_compiled_dir_path(
    *,
    ws_root: Path,
    compiled_dir: str | None,
    console: Console,
    resolve_profile_fn: Any,
    get_sdd_paths_fn: Any,
) -> Path:
    c_dir = Path(compiled_dir) if compiled_dir else ws_root / ".providence" / "compiled"
    if not c_dir.exists():
        try:
            active_profile = resolve_profile_fn(root=ws_root).type
        except Exception:
            active_profile = "master"
        paths = get_sdd_paths_fn()
        c_dir = (
            paths["master_compiled"]
            if active_profile == "master"
            else paths["client_compiled"]
        )
    if not c_dir.exists():
        console.print(f"[red]ERROR: Compiled directory not found: {c_dir}[/red]")
        console.print("  Hint: Run 'providence governance compile' first.")
        raise typer.Exit(1)
    return c_dir


def perform_artifact_signing_flow(
    *,
    c_dir: Path,
    k_path: Path,
    key_id: str,
    targets: list[str],
    console: Console,
    compiler_runner_factory: Any | None = None,
) -> int:
    """Sign artifacts using the native Ed25519 backend (Go `sdd-compile sign`).

    This path no longer shells out to OpenSSL: signing is delegated to the
    `sdd-compile` binary via `CompilerRunner`, the same Go-native bridge
    already used for `providence governance compile`.
    """
    signed_count = 0
    runner: Any | None = None
    make_runner = compiler_runner_factory or CompilerRunner
    for filename in targets:
        target_path = c_dir / filename
        if not target_path.exists():
            continue
        if runner is None:
            try:
                runner = make_runner()
            except Exception as exc:
                console.print(
                    "[red]ERROR: Native signing backend (sdd-compile) is not "
                    "available.[/red]"
                )
                console.print(f"  Reason: {exc}")
                console.print(f"  Key id: {key_id}")
                console.print(
                    "  Note: full bootstrap defaults to key id 'dev-01'; "
                    f"direct signing with --key-id {key_id} uses {k_path}."
                )
                raise typer.Exit(1) from exc
        profile = "master" if "core" in filename else "client"
        try:
            runner.sign(
                artifact_path=target_path,
                key_path=k_path,
                key_id=key_id,
                profile=profile,
            )
        except Exception as exc:
            console.print(f"[red]ERROR: Signing failed for {filename}: {exc}[/red]")
            raise typer.Exit(1) from exc
        sig_path = target_path.with_suffix(target_path.suffix + ".sig")
        console.print(f"[green]Signed {filename} -> {sig_path.name}[/green]")
        signed_count += 1
    return signed_count


def update_trusted_keyring_flow(
    *, ws_root: Path, k_path: Path, key_id: str, console: Console
) -> None:
    trust_dir = ws_root / ".providence" / "trust"
    trust_dir.mkdir(parents=True, exist_ok=True)
    keyring_path = trust_dir / "trusted-keys.json"
    pub_key_path = k_path.with_suffix(".pub.pem")
    if not pub_key_path.exists():
        return
    pub_pem = pub_key_path.read_text(encoding="utf-8")
    keyring: dict[str, Any] = {"keys": []}
    if keyring_path.exists():
        with contextlib.suppress(Exception):
            keyring = _json.loads(keyring_path.read_text(encoding="utf-8"))
    keys = keyring.setdefault("keys", [])
    existing = next((item for item in keys if item.get("key_id") == key_id), None)
    if existing:
        existing["public_key_pem"] = pub_pem
        existing["status"] = "active"
    else:
        keys.append(
            {
                "key_id": key_id,
                "public_key_pem": pub_pem,
                "status": "active",
                "not_before": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
    keyring_path.write_text(_json.dumps(keyring, indent=2), encoding="utf-8")
    console.print(f"[green]Updated keyring at {keyring_path}[/green]")


def resolve_sign_targets(
    *,
    ws_root: Path,
    source: bool,
    compiled_dir: str | None,
    console: Console,
    resolve_compiled_dir_fn: Any,
) -> tuple[Path, list[str]]:
    if source:
        return ws_root / ".providence" / "source", ["governance-core.json"]
    return resolve_compiled_dir_fn(
        ws_root=ws_root, compiled_dir=compiled_dir, console=console
    ), ["governance-core.json", "governance-client.json"]
