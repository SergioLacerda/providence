#!/usr/bin/env python3
"""
Thin wrapper around providence_core.governance.handshake for CLI/tool usage.

The canonical implementation lives in:
    packages/core/providence_core/src/providence_core/governance/handshake.py

This file re-exports all public symbols for backwards compatibility with
scripts and tools that import directly from this path.
"""

import sys
from pathlib import Path


def _bootstrap_providence_core() -> None:
    """Add providence_core src to sys.path when running as a script (not installed)."""
    # Walk up from this file's location looking for the monorepo root
    # (identified by packages/core/providence_core/src existing)
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        src = candidate / "packages" / "core" / "providence_core" / "src"
        if src.is_dir():
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))
            return

    raise ImportError(
        "Could not locate packages/core/providence_core/src from any parent of "
        f"{__file__}. Install providence-core or run from the repo root."
    )


try:
    from providence_core.governance.handshake import (
        AgentHandshakeProtocol,
        HandshakeReport,
        ValidationResult,
    )
except ModuleNotFoundError:
    _bootstrap_providence_core()
    from providence_core.governance.handshake import (  # noqa: E402
        AgentHandshakeProtocol,
        HandshakeReport,
        ValidationResult,
    )

__all__ = ["AgentHandshakeProtocol", "HandshakeReport", "ValidationResult"]


# Exit-code semantics (documented):
#   0  HEALTHY
#   1  NOT_INITIALIZED or MISCONFIGURED
#   2  NOT_CONNECTED or unexpected state
_EXIT_CODES = {
    "HEALTHY": 0,
    "NOT_INITIALIZED": 1,
    "MISCONFIGURED": 1,
    "NOT_CONNECTED": 2,
}


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Agent Handshake Protocol — smart context validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  HEALTHY\n"
            "  1  NOT_INITIALIZED or MISCONFIGURED\n"
            "  2  NOT_CONNECTED or unexpected state\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["silent", "compact", "verbose"],
        default="compact",
        help="Output verbosity (default: compact)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force recheck (skip cache)"
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output as JSON"
    )
    args = parser.parse_args()

    try:
        ahp = AgentHandshakeProtocol()
        state, report = ahp.validate(output_mode=args.mode, force_recheck=args.force)
    except Exception as exc:
        if args.as_json:
            print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: Handshake protocol failed: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        data = {
            "state": state,
            "confidence": report.confidence,
            "checks": report.checks,
            "actions": report.actions,
            "suggestions": getattr(report, "suggestions", []),
            "cached": report.cached,
        }
        print(json.dumps(data, indent=2))
    else:
        print(ahp.format_output(state, report, mode=args.mode))

    return _EXIT_CODES.get(state, 2)


if __name__ == "__main__":
    sys.exit(main())
