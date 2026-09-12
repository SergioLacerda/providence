#!/usr/bin/env python3
"""Core/compiler/runtime contract gate.

Runs a curated invariant suite that covers compile outputs, loader validation,
runtime handshake/drift behavior, and canonical contract schema checks.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

SUITE = [
    "tests/contract/test_governance_schema.py",
    "tests/unit/test_governance_compiler.py",
    "tests/unit/test_providence_core_loader.py",
    "packages/core/providence_runtime/tests/test_runtime_contract.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run core/compiler/runtime contract invariant suite."
    )
    parser.add_argument(
        "--mode",
        choices=["warn", "enforce"],
        default="enforce",
        help="warn returns 0 on failures; enforce returns non-zero.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional JSON diagnostics output path.",
    )
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "pytest", "-q", *SUITE]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # nosec B603

    ok = result.returncode == 0
    payload = {
        "gate": "core-compiler-runtime-contract",
        "ok": ok,
        "mode": args.mode,
        "suite": SUITE,
        "returncode": result.returncode,
        "stdout_tail": "\n".join(result.stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(result.stderr.splitlines()[-40:]),
        "error_code": None if ok else "CONTRACT_INVARIANT_VIOLATION",
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if ok:
        print("PASS: CORE_COMPILER_RUNTIME_CONTRACT_OK")
        return 0

    print("FAIL: CONTRACT_INVARIANT_VIOLATION")
    print("Run the contract suite locally:")
    print("  " + " ".join(cmd))
    if payload["stdout_tail"]:
        print("--- pytest stdout (tail) ---")
        print(payload["stdout_tail"])
    if payload["stderr_tail"]:
        print("--- pytest stderr (tail) ---")
        print(payload["stderr_tail"])

    if args.mode == "warn":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
