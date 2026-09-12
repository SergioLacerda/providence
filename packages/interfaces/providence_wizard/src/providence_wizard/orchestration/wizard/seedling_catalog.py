"""Central catalog of wizard seedling selection options.

Every downstream stage (interactive selector, generation, template deployment,
validation, hook adapter scope) should resolve "what was selected" through
this module instead of re-deriving its own list of keys/groups.
"""

from __future__ import annotations

from dataclasses import dataclass

CORE = "CORE"
IDE = "IDE"
AGENTS = "AGENTS"
OPTIONAL = "OPTIONAL"

GROUP_ORDER = (CORE, IDE, AGENTS, OPTIONAL)


@dataclass(frozen=True)
class SeedlingOption:
    """A single selectable seedling/bootstrap option."""

    key: str
    group: str
    description: str
    default: bool = True
    hook_capable: bool = False


CATALOG: tuple[SeedlingOption, ...] = (
    SeedlingOption("governance", CORE, "GAP v1.0 auto-activation"),
    SeedlingOption("agents-md", CORE, "AGENTS.md"),
    SeedlingOption("prompt-commands", CORE, "prompt templates"),
    SeedlingOption("activation-guide", CORE, "ACTIVATION_GUIDE.md"),
    SeedlingOption("verify", CORE, "verify.py"),
    SeedlingOption("vscode", IDE, "VS Code"),
    SeedlingOption("cursor", IDE, "Cursor IDE"),
    SeedlingOption("antigravity", IDE, "Antigravity", default=False),
    SeedlingOption("claude", AGENTS, "Claude / Claude Code", hook_capable=True),
    SeedlingOption("codex", AGENTS, "Codex", hook_capable=True),
    SeedlingOption("gemini", AGENTS, "Gemini", hook_capable=True),
    SeedlingOption("copilot", AGENTS, "GitHub Copilot"),
    SeedlingOption(
        "ci", OPTIONAL, "CI/CD workflow (sdd-validation.yml)", default=False
    ),
    SeedlingOption("compliance", OPTIONAL, "compliance.seed.json", default=False),
    SeedlingOption(
        "personal-overlay", OPTIONAL, "personal skill overlay", default=False
    ),
)

CATALOG_BY_KEY: dict[str, SeedlingOption] = {option.key: option for option in CATALOG}

# Recommended default: everything except OPTIONAL-group options and any
# option explicitly marked `default=False`. This is what "no selection" means
#  it is deliberately NOT "generate everything" (CI/CD and
# compliance artifacts are opt-in only).
RECOMMENDED_DEFAULT: frozenset[str] = frozenset(
    option.key for option in CATALOG if option.default
)

HOOK_CAPABLE_AGENTS: frozenset[str] = frozenset(
    option.key for option in CATALOG if option.hook_capable
)


def grouped_options() -> list[tuple[str, list[SeedlingOption]]]:
    """Return catalog options grouped in display order."""
    groups: dict[str, list[SeedlingOption]] = {group: [] for group in GROUP_ORDER}
    for option in CATALOG:
        groups[option.group].append(option)
    return [(group, groups[group]) for group in GROUP_ORDER if groups[group]]


def resolve_selection(selected: set[str] | None) -> set[str]:
    """Resolve a user selection to a concrete set of keys.

    `None` means "no explicit selection was made" and resolves to the
    recommended default (core + IDEs + agents, excluding CI/
    compliance). An explicit (possibly empty) set is returned unchanged.
    """
    if selected is None:
        return set(RECOMMENDED_DEFAULT)
    return set(selected)
