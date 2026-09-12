"""Context."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from providence_integration.engine.types import IntegrationSpec, RuntimeContext


@dataclass
class ExecutionContext:
    """Holds runtime state for an integration flow execution."""

    spec_dir: Path
    working_dir: Path
    isolation_enabled: bool = False
    data: RuntimeContext = field(default_factory=lambda: cast(RuntimeContext, {}))
    _temp_dir: Path | None = None

    @classmethod
    def from_spec(cls, spec: IntegrationSpec, spec_dir: Path) -> ExecutionContext:
        """From Spec."""
        import os

        context_spec = spec.get("context", {})

        isolation = bool(context_spec.get("isolation", False))
        configured_working_dir = context_spec.get("working_dir")
        temp_dir: Path | None = None

        if isolation or configured_working_dir == "temp":
            temp_dir = Path(tempfile.mkdtemp(prefix="sdd-doctor-"))
            working_dir = temp_dir
            isolation = True
        elif configured_working_dir:
            # Use explicit home directory expansion from environment
            # to support mocking in tests. Check HOME first (for test compatibility),
            # then USERPROFILE (Windows default), then Path.home() as fallback.
            working_dir_str = str(configured_working_dir)
            if working_dir_str.startswith("~"):
                # Try environment variables in order: HOME, USERPROFILE, then Path.home()
                # On Windows, HOME is checked first to support test mocking
                home = os.environ.get("HOME")
                if not home:
                    home = os.environ.get("USERPROFILE")
                if not home:
                    home = str(Path.home())
                working_dir_str = home + working_dir_str[1:]
            working_dir = Path(working_dir_str).resolve()
            working_dir.mkdir(parents=True, exist_ok=True)
        else:
            working_dir = Path.cwd()

        context = cls(
            spec_dir=spec_dir,
            working_dir=working_dir,
            isolation_enabled=isolation,
            _temp_dir=temp_dir,
        )
        context.data["working_dir"] = working_dir
        return context

    def as_dict(self) -> RuntimeContext:
        """Return the mutable dictionary expected by runners/assertions."""
        return self.data

    def cleanup(self) -> None:
        """Cleanup."""
        if self._temp_dir is not None:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None
