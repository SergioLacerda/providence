"""Pure helper functions for test and CI-validate commands."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import typer


def _check_import(module: str) -> bool:
    """Try a real import (not just find_spec) to catch broken packages."""
    try:
        __import__(module)
        return True
    except Exception:
        return False


def _run_script(script_path: str, extra_args: list[str], cwd: str) -> int:
    from providence_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    # Match CI behavior on Windows consoles with limited encodings.
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        [sys.executable, script_path] + extra_args,
        cwd=cwd,
        env=env,
    )
    return result.returncode


def _run_cli(args: list[str], cwd: str) -> int:
    from providence_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        [sys.executable, "-m", "providence_cli"] + args, cwd=cwd, env=env
    )
    return result.returncode


def _run_pytest(args: list[str], cwd: str) -> int:
    from providence_core.utils.process import SafeProcessRunner

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run([sys.executable, "-m", "pytest"] + args, cwd=cwd, env=env)
    return result.returncode


def _resolve_golden_path(root: Path) -> Path:
    return root / ".providence" / "runtime" / "golden-ast.json"


def _find_artifact(root: Path) -> Path | None:
    """Return the compiled governance-core.json from canonical .providence location."""
    candidate = root / ".providence" / "compiled" / "governance-core.json"
    return candidate if candidate.exists() else None


def _save_golden(golden_path: Path, current_ast: Any) -> None:
    """Save the current AST as the golden snapshot."""
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(current_ast.to_json(), encoding="utf-8")
    typer.echo(f"Golden snapshot updated: {golden_path}")
    typer.echo(
        f"  Items: {len(current_ast.items)}, fingerprint: {current_ast.source_fingerprint[:12]}"
    )


def _print_diff(diff: Any) -> None:
    """Print a formatted diff report of breaking/non-breaking/added changes."""
    if diff.breaking_changes:
        typer.echo(f"\n  BREAKING changes ({len(diff.breaking_changes)}):")
        for entry in diff.breaking_changes:
            typer.echo(
                f"    [{entry.item_id}] {entry.change_type}: {entry.before!r}  {entry.after!r}"
            )

    if diff.non_breaking_changes:
        typer.echo(f"\n  Non-breaking changes ({len(diff.non_breaking_changes)}):")
        for entry in diff.non_breaking_changes:
            field_info = f" ({entry.field})" if entry.field else ""
            typer.echo(
                f"    [{entry.item_id}]{field_info}: {entry.before!r}  {entry.after!r}"
            )

    if diff.added_items:
        typer.echo(f"\n  Added ({len(diff.added_items)}):")
        for entry in diff.added_items:
            typer.echo(f"    + [{entry.item_id}] {entry.after}")


def _load_golden_ast(golden_path: Path) -> Any:
    """Load golden AST from file; raise typer.Exit(1) on error."""
    from providence_core.governance.ast import GovernanceAST

    try:
        return GovernanceAST.from_dict(
            json.loads(golden_path.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        typer.echo(f"ERROR: Failed to load golden snapshot: {exc}", err=True)
        raise typer.Exit(1) from exc


def run_review_golden(
    root: Path,
    update: bool,
    fail_on_breaking: bool,
    artifact: Path | None,
    golden: Path | None,
) -> None:
    """Compare current compiled artifact against the golden AST snapshot."""
    try:
        from providence_core.governance.ast import GovernanceAST
    except ImportError:
        typer.echo(
            "ERROR: providence_core.governance.ast is not importable. Run 'providence setup run'.",
            err=True,
        )
        raise typer.Exit(1) from None

    golden_path = golden or _resolve_golden_path(root)
    artifact_path = artifact or _find_artifact(root)

    if artifact_path is None:
        typer.echo(
            "ERROR: No compiled artifact found. Run 'providence governance compile' first.",
            err=True,
        )
        typer.echo(
            "  Next: run 'providence governance compile' to build artifacts", err=True
        )
        raise typer.Exit(1)

    try:
        current_ast = GovernanceAST.from_compiled_json(artifact_path)
    except Exception as exc:
        typer.echo(f"ERROR: Failed to load artifact: {exc}", err=True)
        raise typer.Exit(1) from exc

    if update:
        _save_golden(golden_path, current_ast)
        return

    if not golden_path.exists():
        _save_golden(golden_path, current_ast)
        typer.echo(f"Golden baseline initialised: {golden_path} (status: new)")
        return

    golden_ast = _load_golden_ast(golden_path)
    diff = golden_ast.diff(current_ast)

    typer.echo(
        f"Comparing artifact ({artifact_path.name}) against golden ({golden_path.name}):"
    )
    typer.echo(f"  Summary: {diff.summary()}")

    if diff.is_clean:
        typer.echo("  Status: CLEAN  no changes detected.")
        return

    _print_diff(diff)

    if diff.has_breaking_changes and fail_on_breaking:
        typer.echo(
            "\n  Next: review breaking changes above, then run 'providence test review-golden --update' to accept",
            err=True,
        )
        raise typer.Exit(1)
