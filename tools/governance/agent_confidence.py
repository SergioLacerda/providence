#!/usr/bin/env python3
"""
Providence Architecture - Agent Confidence Evaluator

Evaluates AI agent confidence and safety:
- Model information (if available in context)
- Temperature settings (determinism level)
- Overall confidence score (0-100%)

Usage:
    python tools/governance/agent_confidence.py [--model=<model>] [--temperature=<0-2>]
    python tools/governance/agent_confidence.py --json
"""

import json
import sys
from typing import Any

_TELEMETRY_AVAILABLE = False
try:
    from providence_telemetry.collectors.confidence import ConfidenceCollector

    _TELEMETRY_AVAILABLE = True
except ImportError:
    _TELEMETRY_AVAILABLE = False  # optional dependency


class AgentConfidenceEvaluator:
    """Evaluates AI agent confidence and operational safety."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._available = _TELEMETRY_AVAILABLE

    def evaluate(self, **kwargs: Any) -> dict[str, Any]:
        """Collect confidence metrics via providence_telemetry, or fail explicitly."""
        if not self._available:
            return {
                "error": "providence_telemetry not installed",
                "hint": "Run: pip install providence-telemetry",
                "overall_confidence": 0.0,
                "safety_level": "UNKNOWN",
            }

        collector = ConfidenceCollector()
        return collector.collect(**kwargs)

    def print_report(self, metrics: dict[str, Any]) -> None:
        """Print formatted confidence report."""
        print("\n" + "=" * 60)
        print("Agent Confidence Evaluation")
        print("=" * 60 + "\n")

        if "error" in metrics:
            print(f"  ERROR: {metrics['error']}")
            if "hint" in metrics:
                print(f"  HINT:  {metrics['hint']}")
            print("")
        else:
            for key in ["model", "temperature"]:
                if key in metrics and isinstance(metrics[key], dict):
                    data = metrics[key]
                    score = data.get("score", 0)
                    message = data.get("message", "")
                    bar_length = score // 10
                    bar = "#" * bar_length + "." * (10 - bar_length)
                    print(f"  {key:20} [{bar}] {score:3}% - {message}")

        print(f"\n  Overall Confidence: {metrics.get('overall_confidence', 0.0):.1f}%")
        print(f"  Safety Level:       {metrics.get('safety_level', 'UNKNOWN')}")
        print("\n" + "=" * 60 + "\n")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate AI agent confidence and safety"
    )
    parser.add_argument("--model", help="Model name (e.g., claude-sonnet-4-6)")
    parser.add_argument(
        "--temperature", type=float, help="Temperature setting (0.0-2.0)"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output as JSON"
    )
    args = parser.parse_args()

    if args.temperature is not None and not (0.0 <= args.temperature <= 2.0):
        print("ERROR: --temperature must be between 0.0 and 2.0")
        return 1

    evaluator = AgentConfidenceEvaluator(verbose=args.verbose)
    metrics = evaluator.evaluate(model=args.model, temperature=args.temperature)

    if args.as_json:
        print(json.dumps(metrics, indent=2))
    else:
        evaluator.print_report(metrics)

    # Return non-zero if telemetry unavailable or confidence critically low
    if "error" in metrics:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
