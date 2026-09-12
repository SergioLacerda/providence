"""Module-level helper functions for IntelligentSeedlingsGenerator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import read_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME


def _write_deployment_manifest(
    output_base: Path,
    spec_fingerprint: str,
    generated_at: str,
    log_fn: Any,
) -> None:
    """Write DEPLOYMENT_MANIFEST.json with fingerprints of all bootstrap files."""
    bootstrap_candidates = {
        "CLAUDE.md": "redirector",
        "GEMINI.md": "redirector",
        ".gemini/gemini-instructions.md": "redirector",
        ".github/copilot-instructions.md": "redirector",
        f"{RUNTIME_DIRNAME}/agent-instructions.md": "source-of-truth",
    }
    seed_candidates = {
        f"{RUNTIME_DIRNAME}/seedlings/governance.seed.json": "seed",
        f"{RUNTIME_DIRNAME}/seedlings/vscode.seed.json": "seed",
        f"{RUNTIME_DIRNAME}/seedlings/cursor.seed.json": "seed",
        f"{RUNTIME_DIRNAME}/seedlings/gemini.seed.json": "seed",
        f"{RUNTIME_DIRNAME}/seedlings/codex.seed.json": "seed",
    }
    bootstrap_files = {
        rel: {"fingerprint": spec_fingerprint, "type": ftype}
        for rel, ftype in bootstrap_candidates.items()
        if (output_base / rel).exists()
    }
    seed_files = {
        rel: {"fingerprint": spec_fingerprint, "type": ftype}
        for rel, ftype in seed_candidates.items()
        if (output_base / rel).exists()
    }
    manifest = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "governance_fingerprint": spec_fingerprint,
        "wizard_version": "3.0",
        "bootstrap_files": bootstrap_files,
        "seed_files": seed_files,
    }
    try:
        manifest_path = output_base / "DEPLOYMENT_MANIFEST.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        log_fn(" Written DEPLOYMENT_MANIFEST.json")
    except Exception as e:
        log_fn(f"  Could not write DEPLOYMENT_MANIFEST.json: {e}")


def _validate_awareness_pack(
    output_base: Path,
    seedlings_dir: Path,
    prompt_commands_mode: str,
) -> dict[str, Any]:
    """Check that all required agent-awareness artifacts were generated."""
    missing_items: list[str] = []
    prompt_dir = output_base / ".github" / "prompts"
    cursor_cmd = output_base / ".cursor" / "rules" / "sdd-commands.mdc"
    gemini_cmd = output_base / ".gemini" / "commands.md"
    claude_file = output_base / "CLAUDE.md"
    agents_file = output_base / "AGENTS.md"
    activation_guide = seedlings_dir / "ACTIVATION_GUIDE.md"

    prompt_files = list(prompt_dir.glob("*.prompt.md")) if prompt_dir.exists() else []
    if not prompt_files:
        missing_items.append(".github/prompts/*.prompt.md")
    if not cursor_cmd.exists():
        missing_items.append(".cursor/rules/sdd-commands.mdc")
    if not gemini_cmd.exists():
        missing_items.append(".gemini/commands.md")
    if not claude_file.exists():
        missing_items.append("CLAUDE.md")
    if not agents_file.exists():
        missing_items.append("AGENTS.md")

    if not activation_guide.exists():
        missing_items.append(f"{RUNTIME_DIRNAME}/seedlings/ACTIVATION_GUIDE.md")
    else:
        content = read_text_utf8(activation_guide)
        required_snippets = [
            "providence skills run sdd-validate-governance",
            "providence skills run sdd-diagnose",
            "providence runtime status",
            "providence governance validate",
            "providence ask --full",
            "providence governance compile",
        ]
        for snippet in required_snippets:
            if snippet not in content:
                missing_items.append(f"activation_guide_missing:{snippet}")

    status = "ok" if not missing_items else "incomplete"
    return {
        "status": status,
        "mode": prompt_commands_mode,
        "missing_items": missing_items,
    }
