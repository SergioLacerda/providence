"""Platform constants, verified limits and paths of the prompt-submit hook."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.constants import RUNTIME_DIRNAME

SUPPORTED_PROMPT_HOOK_AGENTS = frozenset(
    {"claude", "codex", "gemini", "copilot", "devin"}
)
# The hook bounds its own `providence ask` subprocess; the platform must allow
# strictly more, otherwise it can kill the hook at the same instant and the
# degraded-mode diagnostic is never delivered.
HOOK_INTERNAL_TIMEOUT_SECONDS = 10
PLATFORM_HOOK_TIMEOUT_SECONDS = 15


# Limits verified against each platform's official documentation (2026-10-11).
# Shown by generation and by `providence governance hook status`; a hook that is
# untrusted, or whose output the platform drops, is silent in the same way a
# dead adapter is, so the limit is stated instead of implied.
PLATFORM_NOTICES: dict[str, str] = {
    "codex": (
        "Codex trusts a project hook by the hash of its exact definition and "
        "only when the project .codex/ layer is trusted; a regenerated or "
        "changed definition is skipped until it is reviewed again in /hooks "
        "(Codex warns at startup when hooks need review)."
    ),
    "copilot": (
        "Copilot CLI drops the output of config-file userPromptSubmitted hooks "
        "and documents no additionalContext for UserPromptSubmit; context "
        "injection is not guaranteed there."
    ),
    "devin": (
        "Devin CLI loads project hooks from .devin/hooks.v1.json and, by "
        "default, from .claude/settings.json; it documents neither how the two "
        "merge, nor the hook's working directory, nor the shell on Windows, so "
        "exactly one registration is written and the launcher anchors on "
        "DEVIN_PROJECT_DIR."
    ),
}


class HookGenerationError(RuntimeError):
    """Hook adapter generation refused to touch user content it cannot trust.

    Raised before anything is written: a malformed settings file or an input
    retired by an earlier rename is reported and left byte-identical.
    """


CENTRAL_PROMPT_SUBMIT_HOOK = (
    Path(RUNTIME_DIRNAME) / "runtime" / "hooks" / "prompt-submit.py"
)
COPILOT_HOOK_FILE = Path(".github") / "hooks" / "providence-prompt-submit.json"
# Devin CLI's standalone hook file: the events sit at the top level of the
# object, with no "hooks" wrapper key (docs.devin.ai/cli/extensibility/hooks).
DEVIN_HOOK_FILE = Path(".devin") / "hooks.v1.json"
# Set by Devin to the project root; its hook working directory is undocumented.
DEVIN_PROJECT_DIR_ENV = "DEVIN_PROJECT_DIR"
