"""Runtime execution helper for Phase 6 seedlings generation."""

import json
from collections.abc import Callable
from pathlib import Path

from providence_wizard.orchestration.phase4_governance_loader import GovernanceLoader
from providence_wizard.orchestration.phase6_seedlings_orchestrator import (
    SeedlingsOrchestrator,
)
from providence_wizard.orchestration.prompt_submit_hooks import (
    SUPPORTED_PROMPT_HOOK_AGENTS,
    PromptSubmitHookGenerator,
)
from providence_wizard.orchestration.wizard.messages import (
    phase6_seedlings_success_message,
)

_HOOK_MODE_SEEDLING_KEYS = {
    "governance",
    "personal-overlay",
    "activation-guide",
    "verify",
    "claude",
    "codex",
    "gemini",
}


def _resolve_governance_paths(
    paths: dict[str, Path], output_base: Path
) -> tuple[Path, Path]:
    """Resolve governance JSON paths with .providence-first precedence."""
    root = paths.get("root", Path.cwd())
    client_compiled = paths.get(
        "client_compiled", root / "generated" / "client" / "compiled"
    )
    core_candidates = [
        root / ".providence" / "compiled" / "governance-core.json",
        root / ".providence" / "source" / "governance-core.json",
        client_compiled / "source" / "governance-core.json",
        output_base / ".providence" / "source" / "governance-core.json",
    ]
    client_candidates = [
        root / ".providence" / "compiled" / "governance-client.json",
        root / ".providence" / "source" / "governance-client.json",
        client_compiled / "source" / "governance-client.json",
        output_base / ".providence" / "source" / "governance-client.json",
    ]

    core_path = next((p for p in core_candidates if p.exists()), core_candidates[0])
    client_path = next(
        (p for p in client_candidates if p.exists()), client_candidates[0]
    )
    return core_path, client_path


def run_phase6_seedlings_generation(
    *,
    wizard_config_path: Path,
    output_base: Path,
    emitter: Callable[[str], None],
    debug: bool = False,
) -> bool:
    """Run Phase 6 governance loading + seedlings generation."""
    from providence_core.utils.environment import get_sdd_paths

    if wizard_config_path.exists():
        with open(wizard_config_path, encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "language": "Python",
            "enforcement_mode": "warn_mode",
            "language_context": {
                "preferred_human_language": "English",
                "preferred_chat_language": "English",
                "preferred_ui_language": "English",
                "preferred_local_docs_language": "English",
            },
        }

    paths = get_sdd_paths()
    governance_core_path, governance_client_path = _resolve_governance_paths(
        paths, output_base
    )

    loader = GovernanceLoader(
        governance_core_path, governance_client_path, verbose=debug
    )
    if not loader.load():
        emitter("   Failed to load governance")
        return False

    orchestrator = SeedlingsOrchestrator(
        output_base=output_base,
        mandates=loader.mandates,
        guidelines_by_category=loader.guidelines_by_category,
        config=config,
        governance_core_path=governance_core_path,
        paths=paths,
        verbose=debug,
    )
    handshake_mode = config.get("handshake_mode", "standard")
    selected = _HOOK_MODE_SEEDLING_KEYS if handshake_mode == "hook" else None
    if handshake_mode == "hook":
        emitter("hook-mode...OK")
    if not orchestrator.generate(selected=selected):
        emitter("   Failed to generate intelligent seedlings")
        return False
    if handshake_mode == "hook":
        agents = set(SUPPORTED_PROMPT_HOOK_AGENTS)
        config["prompt_submit_hook_agents"] = sorted(agents)
        if not PromptSubmitHookGenerator(output_base, agents).generate():
            emitter("   Failed to generate prompt-submit hooks")
            return False
        emitter("hook...OK")

    emitter(phase6_seedlings_success_message(output_base))
    return True
