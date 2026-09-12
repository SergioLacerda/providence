"""Governance SOFT/HARD directive collection for profile gate enforcement."""

from __future__ import annotations


def _collect_gate_directives(
    invoked: str,
    subcommand: str,  # noqa: ARG001
    profile: str,
    state: str,
    sensitive: bool,
) -> list[tuple[str, str, str]]:
    """Collect governance SOFT/HARD directives for the current invocation context.

    Returns a list of (message, next_step, reason) tuples.
    """
    directives: list[tuple[str, str, str]] = []

    # Profile-scoped SOFT directives.
    if invoked == "release" and profile == "client":
        directives.append(
            (
                "SOFT [governance]: 'release' em workspace client exige contexto master.",
                "use 'sdd --profile master release build'",
                "profile-release-client",
            )
        )
    if invoked == "wizard" and profile == "master":
        directives.append(
            (
                "SOFT [governance]: 'wizard' e primario para workspace client.",
                "confirme escopo ou rode em workspace client",
                "profile-wizard-master",
            )
        )
    if invoked == "ask" and state == "NOT_INITIALIZED":
        directives.append(
            (
                "HARD [governance]: 'ask' requires compiled governance. Workspace NOT_INITIALIZED.",
                "providence governance compile && providence runtime status --force",
                "ask-not-initialized",
            )
        )
    elif invoked == "ask" and state == "PARTIAL":
        directives.append(
            (
                "SOFT [governance]: governanca PARTIAL  precisao do ask pode ser reduzida.",
                "providence governance compile",
                "ask-partial",
            )
        )

    # State-scoped HARD directives (Fail-Closed Governance Enforcement).
    if state == "MISCONFIGURED":
        directives.append(
            (
                "HARD [governance]: workspace MISCONFIGURED. Operacao abortada por seguranca.",
                "run 'providence doctor run' para diagnostico e conserte a governanca",
                "state-misconfigured",
            )
        )
    elif state == "NOT_INITIALIZED" and invoked != "wizard" and sensitive:
        directives.append(
            (
                "SOFT [governance]: governanca nao inicializada. Operacao pode ser limitada.",
                "run 'providence governance validate' ou compile a governanca",
                "state-not-initialized",
            )
        )
    elif state == "PARTIAL" and sensitive:
        directives.append(
            (
                "SOFT [governance]: comando sensivel em estado PARTIAL.",
                "run 'providence runtime status --force' e 'providence governance compile'",
                "state-partial-sensitive",
            )
        )

    return directives
