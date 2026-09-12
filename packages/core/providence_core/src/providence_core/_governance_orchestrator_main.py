from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from providence_core._governance_orchestrator_types import PipelineResult


def print_pipeline_result(orchestrator: Any, result: PipelineResult) -> None:
    if result and result.get("full_pipeline_success"):
        print()  # noqa: T201
        print("=" * 60)  # noqa: T201
        print("🎉 PHASE 1 + PHASE 2 COMPLETE")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print()  # noqa: T201
        summary = orchestrator.get_deployment_summary()
        print("📦 Deployment Summary:")  # noqa: T201
        for key, value in summary.items():
            if key == "artifacts":
                print(f"  {key}:")  # noqa: T201
                for artifact_name, artifact_path in value.items():
                    print(f"    - {artifact_name}: {Path(artifact_path).name}")  # noqa: T201
            elif key != "deployment_location":
                print(f"  {key}: {value}")  # noqa: T201
        print()  # noqa: T201
        print(f"✅ Ready for: {summary['next_step']}")  # noqa: T201
        return
    print()  # noqa: T201
    print("❌ Pipeline failed")  # noqa: T201
    sys.exit(1)
