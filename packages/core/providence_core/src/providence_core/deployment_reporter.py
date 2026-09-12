"""Deployment Reporter - Manifest, checklist, and status reporting.

Generates deployment checklists, manifests, and status reports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DeploymentReporter:
    """Static class for deployment reporting operations."""

    @staticmethod
    def generate_checklist(
        runtime_compiled: Path,
        runtime_audit: Path,
        artifacts: tuple[str, str, str, str],
    ) -> dict[str, bool]:
        """Generate deployment checklist.

        Args:
            runtime_compiled: Path to runtime/compiled directory
            runtime_audit: Path to runtime/compiled/audit directory
            artifacts: Tuple of 4 artifact filenames

        Returns:
            Dictionary of checklist items and their status
        """
        return {
            "Compiled files validated": True,
            "Runtime directory created": runtime_compiled.exists(),
            "Core msgpack copied": (runtime_compiled / artifacts[0]).exists(),
            "Client msgpack copied": (runtime_compiled / artifacts[1]).exists(),
            "Core metadata copied": (runtime_audit / artifacts[2]).exists(),
            "Client metadata copied": (runtime_audit / artifacts[3]).exists(),
            "Backup directory created": (runtime_compiled / "backup").exists(),
        }

    @staticmethod
    def generate_manifest(
        runtime_compiled: Path,
        runtime_audit: Path,
        artifacts: tuple[str, str, str, str],
    ) -> dict[str, Any]:
        """Generate deployment manifest and save to file.

        Args:
            runtime_compiled: Path to runtime/compiled directory
            runtime_audit: Path to runtime/compiled/audit directory
            artifacts: Tuple of 4 artifact filenames

        Returns:
            Dictionary containing manifest data
        """
        manifest = {
            "version": "3.0",
            "deployment_date": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "deployment_location": runtime_compiled.as_posix(),
            "artifacts": {
                "core_msgpack": artifacts[0],
                "client_msgpack": artifacts[1],
                "core_metadata": f"audit/{artifacts[2]}",
                "client_metadata": f"audit/{artifacts[3]}",
            },
            "file_count": 4,
            "status": "deployed",
            "ready_for": "wizard_and_agent_runtime",
        }

        # Save manifest
        manifest_file = runtime_audit / "DEPLOYMENT_MANIFEST.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    @staticmethod
    def get_next_steps() -> list[str]:
        """Get next steps after deployment.

        Returns:
            List of next steps to take
        """
        return [
            "1. Review deployment files in runtime/compiled/",
            "2. Run: git add runtime/compiled/",
            "3. Run: git commit -m 'chore(sdd): PHASE 4 deployment - v3.0 pipeline+compiler'",
            "4. Run: git tag -a v3.0-pipeline-compiler-complete -m 'PHASE 1-4 complete'",
            "5. Update CHANGELOG.md with deployment details",
            "6. Ready for PHASE 5: Wizard integration",
        ]

    @staticmethod
    def cleanup_legacy_manifests(repo_root: Path, runtime_compiled: Path) -> None:
        """Remove legacy manifest files.

        Args:
            repo_root: Root of the repository
            runtime_compiled: Path to runtime/compiled directory
        """
        legacy_paths = [
            repo_root / ".providence" / "DEPLOYMENT_MANIFEST.json",
            runtime_compiled / "DEPLOYMENT_MANIFEST.json",
        ]
        for path in legacy_paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                # Best effort cleanup; deployment success should not depend on this.
                pass

    @staticmethod
    def get_deployment_status(
        runtime_compiled: Path,
        runtime_audit: Path,
        artifacts: tuple[str, str, str, str],
    ) -> dict[str, Any]:
        """Get current deployment status.

        Args:
            runtime_compiled: Path to runtime/compiled directory
            runtime_audit: Path to runtime/compiled/audit directory
            artifacts: Tuple of 4 artifact filenames

        Returns:
            Dictionary containing deployment status
        """
        return {
            "deployed": runtime_compiled.exists(),
            "files_present": {
                "core_msgpack": (runtime_compiled / artifacts[0]).exists(),
                "client_msgpack": (runtime_compiled / artifacts[1]).exists(),
                "core_metadata": (runtime_audit / artifacts[2]).exists(),
                "client_metadata": (runtime_audit / artifacts[3]).exists(),
            },
            "location": runtime_compiled.as_posix(),
        }
