"""Generate-phase prerequisite writers: instructions, prompt commands, adapters,
and the mandatory runtime handbook slices.

Split out of `governance_generate_handlers.py` (T2,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from providence_cli.generators.agent_seeds import (
    generate_agent_instruction_files,
    generate_agent_prompt_commands,
)


def write_instruction_files_safe(
    output_base: Path, config: dict[str, Any], *, console: Console
) -> None:
    """Write agent instruction files, logging a warning on failure."""
    try:
        for label, target in generate_agent_instruction_files(output_base, config):
            console.print(f"[green]{label} instructions written to {target}[/green]")
    except Exception as _e:
        console.print(f"[yellow]WARN: could not write instruction files: {_e}[/yellow]")


def write_prompt_commands_safe(
    output_base: Path, config: dict[str, Any], *, console: Console
) -> None:
    """Write agent prompt command files, logging a warning on failure."""
    try:
        for label, target in generate_agent_prompt_commands(output_base, config):
            console.print(f"[green]{label} prompt commands written to {target}[/green]")
    except Exception as _e:
        console.print(
            f"[yellow]WARN: could not write prompt command files: {_e}[/yellow]"
        )


def generate_adapters_safe(output_base: Path, *, console: Console) -> None:
    """Generate adapter files, logging a warning on failure."""
    try:
        from providence_adapters.adapter_generator import AdapterGenerator

        adapter_gen = AdapterGenerator()
        results = adapter_gen.generate(output_dir=output_base)
        for target, result in results.items():
            if result.success and result.files_written:
                console.print(
                    f"[green]Adapters ({target}): {len(result.files_written)} files written[/green]"
                )
            elif result.errors:
                for err in result.errors:
                    console.print(f"[yellow]WARN: adapter {target}: {err}[/yellow]")
    except Exception as _e:
        console.print(f"[yellow]WARN: could not generate adapter files: {_e}[/yellow]")


def generate_runtime_handbook_required(
    output_base: Path, *, console: Console, quiet: bool = False
) -> None:
    """Generate mandatory runtime handbook slices from docs/ source registry."""
    from providence_cli.services.governance_docs_handbook_gen import (
        generate_runtime_handbook,
    )
    from providence_cli.services.governance_docs_sources import DEFAULT_REGISTRY
    from providence_cli.utils.environment import detect_repo_root
    from providence_cli.utils.providence_authority import resolve_workspace_root

    source_root = resolve_workspace_root() or output_base
    if not (source_root / DEFAULT_REGISTRY).exists():
        try:
            # allow_file_fallback=False: this repo's own docs registry must
            # never be substituted for a client workspace's registry under
            # an editable/dev install  see _environment_repo.detect_repo_root.
            repo_root = detect_repo_root(allow_file_fallback=False)
        except RuntimeError:
            repo_root = None
        if repo_root is not None and (repo_root / DEFAULT_REGISTRY).exists():
            source_root = repo_root
    written = generate_runtime_handbook(source_root, runtime_root=output_base)
    if written and not quiet:
        console.print(f"[green]Runtime handbook: {len(written)} files written[/green]")
