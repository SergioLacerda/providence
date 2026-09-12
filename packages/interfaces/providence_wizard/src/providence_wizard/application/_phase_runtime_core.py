"""Runtime bridge from the shell boundary to the current interactive engine."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import cast

from providence_wizard.contracts import WizardInvocation


class PhaseRuntime:
    """Execute the current interactive wizard through a narrow boundary."""

    def __init__(
        self,
        invocation: WizardInvocation,
        runner: Callable[..., bool] | None = None,
    ) -> None:
        self._invocation = invocation
        self._runner = runner

    def execute(self) -> bool:
        """Run the interactive engine with lazy imports."""
        runner = self._runner or self._load_runner()
        return bool(
            runner(
                self._invocation.project_root,
                output_dir=self._invocation.output_path,
                non_interactive=self._invocation.non_interactive,
                custom_governance_path=self._invocation.custom_governance_path,
                debug=self._invocation.debug,
            )
        )

    def _load_runner(self) -> Callable[..., bool]:
        module = importlib.import_module(
            "providence_wizard.application.interactive_wizard"
        )
        return cast(Callable[..., bool], module.run_interactive_wizard)
