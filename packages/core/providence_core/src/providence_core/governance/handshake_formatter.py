"""Handshake output formatting."""

from __future__ import annotations

from typing import Any, Literal

from ._handshake_constants import STATES


class HandshakeFormatter:
    """Formats handshake validation results."""

    STATES = STATES

    def __init__(self) -> None:
        """Initialize formatter."""
        self.gap_status = "ACTIVE"
        self.mandates_loaded: list[str] = []
        self.current_confidence = 100.0

    def format_gap_output(
        self, mode: Literal["silent", "compact", "verbose"] = "compact"
    ) -> str:
        """Format Governance Activation Protocol status."""
        if mode == "silent":
            return ""

        status_emoji = {"ACTIVE": "🟢", "PARTIAL": "🟡", "NOT_ACTIVE": "🔴"}.get(
            self.gap_status, "❓"
        )

        if mode == "compact":
            return f"{status_emoji} SDD Governance: {self.gap_status}"

        output = f"{status_emoji} SDD Governance: {self.gap_status}\n"
        if self.mandates_loaded:
            output += f"  - Mandates: {', '.join(self.mandates_loaded)}\n"
        output += f"  - Confidence: {self.current_confidence:.1f}%"
        return output

    def format_combined_output(
        self,
        state: str,
        report: Any,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Format combined AHP + GAP output."""
        if mode == "silent":
            return ""
        gap_output = self.format_gap_output(mode=mode)
        ahp_output = self.format_output(state, report, mode=mode)
        if mode == "compact":
            return gap_output
        return (gap_output + "\n" + ahp_output) if ahp_output else gap_output

    def _format_compact_output(self, state: str, emoji: str, report: Any) -> str:
        output = f"\nSDD STATUS\nState: {emoji} {state}\n"
        for check in report.checks:
            symbol = "PASS" if check["passed"] else "FAIL"
            output += f"  {symbol} {check['name']}\n"
        if report.actions:
            output += f"\nActions: -> {', '.join(report.actions)}\n"
        return output

    def _format_verbose_output(self, state: str, emoji: str, report: Any) -> str:
        output = "\n" + "=" * 60 + "\n"
        output += f"SDD STATUS REPORT\nState: {emoji} {state}\n"
        output += f"Confidence: {report.confidence}%\n" + "=" * 60 + "\n\n"

        by_layer: dict[str, list[dict[str, Any]]] = {}
        for check in report.checks:
            by_layer.setdefault(check["layer"], []).append(check)

        for layer in [
            "DISCOVERY",
            "LINK_VALIDATION",
            "RUNTIME_VALIDATION",
            "GOVERNANCE_HEALTH",
        ]:
            if layer in by_layer:
                output += f"LAYER: {layer}\n"
                for check in by_layer[layer]:
                    symbol = "PASS" if check["passed"] else "FAIL"
                    output += f"  {symbol} {check['name']}: {check['message']}\n"
                output += "\n"

        if report.cached:
            output += f"Cached ({report.cache_age_seconds}s old)\n"
        if report.actions:
            output += "\nRecommended Actions:\n"
            for action in report.actions:
                output += f"  -> {action}\n"
        output += "=" * 60 + "\n"
        return output

    def format_output(
        self,
        state: str,
        report: Any,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Format handshake result for display."""
        state_info = self.STATES.get(state, {})
        emoji = str(state_info.get("emoji", "?"))

        if mode == "silent":
            return f"SDD: {emoji}"
        if mode == "verbose":
            return self._format_verbose_output(state, emoji, report)
        return self._format_compact_output(state, emoji, report)
