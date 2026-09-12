"""Deployment Validator - File validation and verification.

Handles validation of compiled files and verification of deployment success.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


class DeploymentValidator:
    """Static class for deployment validation operations."""

    @staticmethod
    def validate_compiled_files(
        compiled_dir: Path,
        artifacts: tuple[str, str, str, str],
        metadata_source_fn: Callable[[str], Path],
        bootstrapper: Any,
        emit_fn: Callable[[str], None],
    ) -> bool:
        """Validate that all required compiled files exist and are valid.

        Args:
            compiled_dir: Path to compiled artifacts directory
            artifacts: Tuple of 4 artifact filenames
            metadata_source_fn: Function to resolve metadata file paths
            bootstrapper: ArtifactBootstrapper instance
            emit_fn: Function to emit status messages

        Returns:
            True if all files valid, False otherwise
        """
        bootstrapper.ensure()

        required_files = [
            compiled_dir / artifacts[0],
            compiled_dir / artifacts[1],
            metadata_source_fn(artifacts[2]),
            metadata_source_fn(artifacts[3]),
        ]

        all_exist = True
        for file in required_files:
            if file.exists():
                size_kb = file.stat().st_size / 1024
                emit_fn(f"  ✅ {file.name} ({size_kb:.1f} KB)")
            else:
                emit_fn(f"  ❌ {file.name} MISSING")
                all_exist = False

        # Verify metadata is valid JSON
        for metadata_file in [
            metadata_source_fn("metadata-core.json"),
            metadata_source_fn("metadata-client-template.json"),
        ]:
            try:
                with open(metadata_file, encoding="utf-8") as f:
                    json.load(f)
                emit_fn(f"  ✅ {metadata_file.name} is valid JSON")
            except Exception as e:
                emit_fn(f"  ❌ {metadata_file.name} is not valid JSON: {e}")
                all_exist = False

        return all_exist

    @staticmethod
    def verify_deployment(
        runtime_compiled: Path,
        artifacts: tuple[str, str, str, str],
        emit_fn: Callable[[str], None],
    ) -> bool:
        """Verify that deployment was successful.

        Args:
            runtime_compiled: Path to runtime/compiled directory
            artifacts: Tuple of 4 artifact filenames
            emit_fn: Function to emit status messages

        Returns:
            True if all files deployed, False otherwise
        """
        required_files = [
            artifacts[0],
            artifacts[1],
            f"audit/{artifacts[2]}",
            f"audit/{artifacts[3]}",
        ]

        all_verified = True
        for filename in required_files:
            file_path = runtime_compiled / filename
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                emit_fn(f"  ✅ {filename} deployed ({size_kb:.1f} KB)")
            else:
                emit_fn(f"  ❌ {filename} NOT deployed")
                all_verified = False

        return all_verified
