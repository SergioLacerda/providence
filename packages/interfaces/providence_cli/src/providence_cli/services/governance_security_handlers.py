"""Security-oriented handlers for governance commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from providence_cli.services._governance_security_support import (
    perform_artifact_signing_flow,
    resolve_compiled_dir_path,
    resolve_sign_targets,
    update_trusted_keyring_flow,
)


def run_keygen(*, key_id: str, output_dir: str, console: Console) -> None:
    """Generate an Ed25519 key pair via the native backend (Go `sdd-compile keygen`).

    This path no longer shells out to OpenSSL, so it works on standalone
    installs (notably Windows) where no `openssl` binary is on PATH.
    """
    from providence_core.utils.compiler_runner import CompilerRunner

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    priv_path = out / f"{key_id}.key"
    pub_path = out / f"{key_id}.pub.pem"
    if priv_path.exists():
        console.print(f"[yellow]Key {key_id} already exists at {priv_path}[/yellow]")
        raise typer.Exit(0)

    try:
        runner = CompilerRunner()
    except Exception as exc:
        console.print(
            "[red]ERROR: Native keygen backend (sdd-compile) is not available.[/red]"
        )
        console.print(f"  Reason: {exc}")
        raise typer.Exit(1) from exc

    try:
        runner.keygen(private_key_path=priv_path, public_key_path=pub_path)
    except Exception as exc:
        console.print(f"[red]ERROR: Key generation failed for {key_id}: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]Generated Ed25519 key pair '{key_id}' in {output_dir}[/green]"
    )
    console.print(f"  Private: {priv_path.name} (KEEP SECRET)")
    console.print(f"  Public:  {pub_path.name}")
    console.print(
        "\n[cyan]Next step: providence governance sign --key-id " + key_id + "[/cyan]"
    )


def resolve_compiled_dir(
    *, ws_root: Path, compiled_dir: str | None, console: Console
) -> Path:
    """Resolve compiled governance directory with profile-aware fallback."""
    from providence_core.utils.environment import get_sdd_paths, resolve_profile

    return resolve_compiled_dir_path(
        ws_root=ws_root,
        compiled_dir=compiled_dir,
        console=console,
        resolve_profile_fn=resolve_profile,
        get_sdd_paths_fn=get_sdd_paths,
    )


def _perform_artifact_signing(
    *, c_dir: Path, k_path: Path, key_id: str, targets: list[str], console: Console
) -> int:
    return perform_artifact_signing_flow(
        c_dir=c_dir,
        k_path=k_path,
        key_id=key_id,
        targets=targets,
        console=console,
    )


def _update_trusted_keyring(
    *, ws_root: Path, k_path: Path, key_id: str, console: Console
) -> None:
    update_trusted_keyring_flow(
        ws_root=ws_root,
        k_path=k_path,
        key_id=key_id,
        console=console,
    )


def run_sign(
    *,
    key_id: str,
    key_path: str | None,
    ws_root: Path,
    target_dir: Path,
    targets: list[str],
    console: Console,
) -> None:
    """Sign governance artifacts and update trusted keyring."""
    k_path = (
        Path(key_path)
        if key_path
        else ws_root / ".providence" / "trust" / f"{key_id}.key"
    )
    if not k_path.exists():
        console.print(f"[red]ERROR: Private key not found: {k_path}[/red]")
        console.print(f"  Hint: Run 'providence governance keygen --key-id {key_id}'")
        raise typer.Exit(1)

    signed_count = _perform_artifact_signing(
        c_dir=target_dir, k_path=k_path, key_id=key_id, targets=targets, console=console
    )
    _update_trusted_keyring(
        ws_root=ws_root, k_path=k_path, key_id=key_id, console=console
    )

    if signed_count == 0:
        console.print("[yellow]No artifacts found to sign.[/yellow]")
    else:
        console.print(
            f"[bold green]Successfully signed {signed_count} artifacts.[/bold green]"
        )
        console.print("[cyan]Next step: providence governance audit[/cyan]")


def run_sign_cmd(
    *,
    key_id: str,
    key_path: str | None,
    compiled_dir: str | None,
    source: bool,
    console: Console,
) -> None:
    """Resolve targets from CLI flags and call run_sign."""
    from providence_cli.utils.providence_authority import (
        enforce_path_policy,
        resolve_workspace_root,
    )

    ws_root = resolve_workspace_root()
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    target_dir, targets = resolve_sign_targets(
        ws_root=ws_root,
        source=source,
        compiled_dir=compiled_dir,
        console=console,
        resolve_compiled_dir_fn=resolve_compiled_dir,
    )

    run_sign(
        key_id=key_id,
        key_path=key_path,
        ws_root=ws_root,
        target_dir=target_dir,
        targets=targets,
        console=console,
    )
