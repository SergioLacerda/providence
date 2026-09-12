"""Types."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- Input Models ---


class CommandExecInputs(BaseModel):
    """Inputs for command.exec step type."""

    command: str

    @field_validator("command")
    @classmethod
    def command_non_empty(cls, v: str) -> str:
        """Command Non Empty."""
        if not v.strip():
            raise ValueError("'command' must be non-empty string")
        return v


class FilesystemCreateStructureInputs(BaseModel):
    """Inputs for filesystem.create_structure step type."""

    directories: list[str]


class FilesystemCopyInputs(BaseModel):
    """Inputs for filesystem.copy step type.

    Uses field alias 'from' for the attribute 'from_' (from is a Python keyword).
    """

    from_: str = Field(alias="from")
    to: str

    model_config = ConfigDict(populate_by_name=True)


class ConfigValidateInputs(BaseModel):
    """Inputs for config.validate step type."""

    file: str | None = None


class GitCommitInputs(BaseModel):
    """Inputs for git.commit step type."""

    message: str = "init"


# --- Assertion Spec ---


class StepAssertionSpec(BaseModel):
    """Configuration for an assertion within a step."""

    type: str = ""

    model_config = ConfigDict(extra="allow")


# --- Step Models (Discriminated Union by type) ---


class _BaseStep(BaseModel):
    """Common fields for all step types."""

    id: str = ""
    asserts: list[StepAssertionSpec] = []


class CommandExecStep(_BaseStep):
    """Step that executes a shell command."""

    type: Literal["command.exec"]
    inputs: CommandExecInputs


class FilesystemCreateStructureStep(_BaseStep):
    """Step that creates directories."""

    type: Literal["filesystem.create_structure"]
    inputs: FilesystemCreateStructureInputs


class FilesystemCopyStep(_BaseStep):
    """Step that copies files or directories."""

    type: Literal["filesystem.copy"]
    inputs: FilesystemCopyInputs


class ConfigValidateStep(_BaseStep):
    """Step that validates configuration files."""

    type: Literal["config.validate"]
    inputs: ConfigValidateInputs = Field(default_factory=ConfigValidateInputs)


class GitCommitStep(_BaseStep):
    """Step that creates a git commit."""

    type: Literal["git.commit"]
    inputs: GitCommitInputs = Field(default_factory=GitCommitInputs)


class GenericStep(_BaseStep):
    """Catch-all for unknown/custom step types (no input validation)."""

    type: str
    inputs: dict[str, Any] = {}


class InvalidStep(_BaseStep):
    """Carries ValidationError from Pydantic parsing — blocks execution with structured error."""

    type: str
    inputs: dict[str, Any] = {}
    parse_error: str = ""


# Discriminated union of known step types (for TypeAdapter)
KnownStepSpec = Annotated[
    CommandExecStep
    | FilesystemCreateStructureStep
    | FilesystemCopyStep
    | ConfigValidateStep
    | GitCommitStep,
    Field(discriminator="type"),
]

# Full StepSpec union (known + generic + invalid)
StepSpec = (
    CommandExecStep
    | FilesystemCreateStructureStep
    | FilesystemCopyStep
    | ConfigValidateStep
    | GitCommitStep
    | GenericStep
    | InvalidStep
)

KNOWN_STEP_TYPES = frozenset(
    {
        "command.exec",
        "filesystem.create_structure",
        "filesystem.copy",
        "config.validate",
        "git.commit",
    }
)

# --- Runtime Context (TypedDict for compatibility) ---


class RuntimeContext(TypedDict, total=False):
    """Runtime context passed to step executors."""

    working_dir: Path
    config: dict[str, str]
    last_exit_code: int
    last_stdout: str
    last_stderr: str
    probe: str


ContextSpec = dict[str, Any]


class IntegrationSpec(TypedDict, total=False):
    """Top-level integration specification."""

    context: ContextSpec
    steps: list[StepSpec]
    trusted: bool


# Step types powerful enough to mutate the workspace or run arbitrary
# commands; specs must explicitly declare provenance (`trusted: true`)
# before these are allowed to run.
PRIVILEGED_STEP_TYPES = frozenset({"command.exec", "git.commit"})


# First arg is intentionally Any: each runner receives its own Pydantic inputs
# model (CommandExecInputs, FilesystemCopyInputs, etc.) resolved at runtime.
RunnerCallable = Callable[[Any, RuntimeContext, Path], None]
