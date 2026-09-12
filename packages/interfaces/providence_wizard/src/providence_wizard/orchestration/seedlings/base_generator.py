"""Base Generator."""

from collections.abc import Callable
from pathlib import Path
from typing import Any


class BaseSeedlingGenerator:
    """BaseSeedlingGenerator."""

    def __init__(
        self,
        output_base: Path,
        seedlings_dir: Path,
        config: dict[str, Any],
        spec_fingerprint: str,
        mandate_ids: list[str],
        active_categories: list[str],
        generated_at: str,
        verbose: bool,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.output_base = output_base
        self.seedlings_dir = seedlings_dir
        self.config = config
        self.spec_fingerprint = spec_fingerprint
        self.mandate_ids = mandate_ids
        self.active_categories = active_categories
        self.generated_at = generated_at
        self.verbose = verbose
        self._emit = emitter or print
        self.mandates: list[dict[str, Any]] = []

        # Safeguard: Never mutate the workspace root during tests
        import os

        from providence_core.utils.environment import find_workspace_root

        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if test_output_dir:
            should_block = False
            try:
                # Check if output_base matches the workspace root
                output_resolved = self.output_base.resolve()
                workspace_root = find_workspace_root()
                if workspace_root:
                    workspace_resolved = workspace_root.resolve()
                    if output_resolved == workspace_resolved:
                        should_block = True
            except (OSError, ValueError):
                # Fallback if resolve fails
                pass

            if should_block:
                msg = f"SDD_ISOLATION_ERROR: Mutation of workspace root blocked ({self.output_base})"
                self._emit(f"   {msg}")
                raise PermissionError(msg)

    def log(self, message: str) -> None:
        """Log."""
        if self.verbose:
            self._emit(f"    {message}")
