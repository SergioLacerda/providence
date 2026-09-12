"""Seedling bridge boundary for future extraction from interactive mode."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


class SeedlingBridge:
    """Run seedling generation through a lazy boundary."""

    def generate(
        self,
        wizard_config_path: Path,
        output_base: Path,
        emitter: Any,
        runner: Callable[..., bool] | None = None,
        debug: bool = False,
    ) -> bool:
        """Delegate to the current runtime only when requested."""
        try:
            active_runner = runner or self._load_runner()

            return bool(
                active_runner(
                    wizard_config_path=wizard_config_path,
                    output_base=output_base,
                    emitter=emitter,
                    debug=debug,
                )
            )
        except Exception as exc:
            emitter(f"   Error: {exc}")
            import traceback

            traceback.print_exc()
            return False

    def _load_runner(self) -> Callable[..., bool]:
        """Load the current seedling runtime lazily."""
        from providence_wizard.orchestration.wizard.seedlings_runtime import (
            run_phase6_seedlings_generation,
        )

        return run_phase6_seedlings_generation
