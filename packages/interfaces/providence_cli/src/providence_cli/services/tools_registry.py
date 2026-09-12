"""Registry contract for repository-local developer tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

SUPPORTED_SCHEMA_VERSIONS = {"1"}
SUPPORTED_VISIBILITIES = {"public", "internal", "deprecated", "project"}
SUPPORTED_STATUSES = {"active", "experimental", "deprecated"}
SUPPORTED_RUNNERS = {"uv-python", "python-module", "go-project", "external"}


class ToolsRegistryError(ValueError):
    """Raised when `tools/registry.yaml` violates the manifest contract."""


@dataclass(frozen=True)
class ToolEntry:
    """One curated tool registry entry."""

    id: str
    path: str
    visibility: str
    status: str
    runner: str
    description: str
    replacement: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    docs_refs: list[str] = field(default_factory=list)
    ci_consumers: list[str] = field(default_factory=list)
    allow_direct_run: bool = False
    module: str | None = None

    @property
    def legacy_name(self) -> str:
        """Return the legacy path accepted by `sdd tools run`."""
        return self.path.removeprefix("tools/")

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the entry."""
        payload: dict[str, Any] = {
            "id": self.id,
            "path": self.path,
            "visibility": self.visibility,
            "status": self.status,
            "runner": self.runner,
            "description": self.description,
            "allow_direct_run": self.allow_direct_run,
        }
        for key in ("replacement", "category", "module"):
            value = getattr(self, key)
            if value:
                payload[key] = value
        if self.tags:
            payload["tags"] = self.tags
        if self.docs_refs:
            payload["docs_refs"] = self.docs_refs
        if self.ci_consumers:
            payload["ci_consumers"] = self.ci_consumers
        return payload


@dataclass(frozen=True)
class ToolsRegistry:
    """Loaded tools registry."""

    path: Path
    schema_version: str
    tools: tuple[ToolEntry, ...]

    def resolve(self, name: str) -> ToolEntry | None:
        """Resolve a manifest ID, full path, or legacy relative path."""
        for tool in self.tools:
            if name in {tool.id, tool.path, tool.legacy_name}:
                return tool
        return None


def load_tools_registry(repo_root: Path) -> ToolsRegistry | None:
    """Load `tools/registry.yaml` when present."""

    registry_path = repo_root / "tools" / "registry.yaml"
    if not registry_path.exists():
        return None

    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ToolsRegistryError(f"invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ToolsRegistryError("registry root must be a mapping")

    schema_version = raw.get("schema_version")
    if (
        not isinstance(schema_version, str)
        or schema_version not in SUPPORTED_SCHEMA_VERSIONS
    ):
        raise ToolsRegistryError("unsupported or missing schema_version")

    raw_tools = raw.get("tools")
    if not isinstance(raw_tools, list):
        raise ToolsRegistryError("tools must be a list")

    seen_ids: set[str] = set()
    entries: list[ToolEntry] = []
    for index, raw_tool in enumerate(raw_tools):
        if not isinstance(raw_tool, dict):
            raise ToolsRegistryError(f"tools[{index}] must be a mapping")
        entry = _parse_entry(raw_tool, index)
        if entry.id in seen_ids:
            raise ToolsRegistryError(f"duplicate tool id: {entry.id}")
        seen_ids.add(entry.id)
        entries.append(entry)

    return ToolsRegistry(
        path=registry_path,
        schema_version=schema_version,
        tools=tuple(entries),
    )


def _parse_entry(raw: dict[str, Any], index: int) -> ToolEntry:
    required = ("id", "path", "visibility", "status", "runner", "description")
    for field_name in required:
        value = raw.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ToolsRegistryError(f"tools[{index}].{field_name} is required")

    path = raw["path"]
    _validate_tools_path(path, index)

    visibility = raw["visibility"]
    if visibility not in SUPPORTED_VISIBILITIES:
        raise ToolsRegistryError(f"tools[{index}].visibility is invalid: {visibility}")

    status = raw["status"]
    if status not in SUPPORTED_STATUSES:
        raise ToolsRegistryError(f"tools[{index}].status is invalid: {status}")

    runner = raw["runner"]
    if runner not in SUPPORTED_RUNNERS:
        raise ToolsRegistryError(f"tools[{index}].runner is invalid: {runner}")

    return ToolEntry(
        id=raw["id"],
        path=path,
        visibility=visibility,
        status=status,
        runner=runner,
        description=raw["description"],
        replacement=_optional_str(raw, "replacement"),
        category=_optional_str(raw, "category"),
        tags=_optional_str_list(raw, "tags", index),
        docs_refs=_optional_str_list(raw, "docs_refs", index),
        ci_consumers=_optional_str_list(raw, "ci_consumers", index),
        allow_direct_run=bool(raw.get("allow_direct_run", False)),
        module=_optional_str(raw, "module"),
    )


def _validate_tools_path(path: str, index: int) -> None:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        raise ToolsRegistryError(f"tools[{index}].path must be repository-relative")
    if not path.startswith("tools/"):
        raise ToolsRegistryError(f"tools[{index}].path must stay under tools/")
    if ".." in pure_path.parts:
        raise ToolsRegistryError(f"tools[{index}].path must stay under tools/")


def _optional_str(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolsRegistryError(f"{key} must be a non-empty string when present")
    return value


def _optional_str_list(raw: dict[str, Any], key: str, index: int) -> list[str]:
    value = raw.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ToolsRegistryError(f"tools[{index}].{key} must be a list of strings")
    return list(value)
