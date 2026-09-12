"""Governance loader public module with patch-friendly imports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import msgpack

from providence_core.utils._governance_loader_support import (
    resolve_existing_metadata_path,
    resolve_metadata_path,
)
from providence_core.utils._template_generator import TemplateGenerator
from providence_core.utils.environment import get_sdd_paths, resolve_profile


class GovernanceLoader:
    """Load compiled governance artifacts and derived metadata for consumers."""

    def __init__(self, compiled_dir: str | None = None):
        paths = get_sdd_paths()
        if compiled_dir is None:
            try:
                self.compiled_dir = paths[
                    "master_compiled"
                    if resolve_profile().type == "master"
                    else "client_compiled"
                ]
            except Exception:
                self.compiled_dir = paths["master_compiled"]
        else:
            self.compiled_dir = Path(compiled_dir)
        self.packages_data: dict[str, Any] | None = None
        self._client_data: dict[str, Any] | None = None
        self.packages_metadata: dict[str, Any] | None = None
        self._client_metadata: dict[str, Any] | None = None
        self._core_context_source = "none"

    def _resolve_metadata_path(self, filename: str) -> Path:
        """Return the canonical compiled/audit/<filename> metadata path."""
        return resolve_metadata_path(filename, self.compiled_dir)

    def load_compiled_binary(self, filepath: Path) -> dict[str, Any]:
        """Load a compiled msgpack artifact from disk."""
        if not filepath.exists():
            raise FileNotFoundError(f"Binary file not found: {filepath}")
        return cast(dict[str, Any], msgpack.unpackb(filepath.read_bytes(), raw=False))

    def load_core(self) -> dict[str, Any]:
        """Load the compiled governance core artifact and metadata."""
        filepath = self.compiled_dir / "governance-core.compiled.msgpack"
        if not filepath.exists():
            raise FileNotFoundError(f"Core msgpack not found: {filepath}")
        self.packages_data = self.load_compiled_binary(filepath)
        self.packages_metadata = json.loads(
            resolve_existing_metadata_path(
                "metadata-core.json", self.compiled_dir
            ).read_text(encoding="utf-8")
        )
        self._core_context_source = "msgpack"
        return self.packages_data

    def load_client(self, client_dir: Path | None = None) -> dict[str, Any]:
        """Load the compiled client governance artifact and metadata."""
        base_dir = client_dir or self.compiled_dir
        filepath = base_dir / "governance-client-template.compiled.msgpack"
        if not filepath.exists() and client_dir is not None:
            base_dir, filepath = (
                self.compiled_dir,
                self.compiled_dir / "governance-client-template.compiled.msgpack",
            )
        if not filepath.exists():
            raise FileNotFoundError(f"Client msgpack not found: {filepath}")
        self._client_data = self.load_compiled_binary(filepath)
        self._client_metadata = json.loads(
            resolve_existing_metadata_path(
                "metadata-client-template.json", base_dir
            ).read_text(encoding="utf-8")
        )
        return self._client_data

    def _load_metadata_only(self) -> None:
        self.packages_metadata = json.loads(
            resolve_existing_metadata_path(
                "metadata-core.json", self.compiled_dir
            ).read_text(encoding="utf-8")
        )
        self._client_metadata = json.loads(
            resolve_existing_metadata_path(
                "metadata-client-template.json", self.compiled_dir
            ).read_text(encoding="utf-8")
        )

    def _require_core_data(self) -> dict[str, Any]:
        return self.packages_data or self.load_core()

    def _require_client_data(self) -> dict[str, Any]:
        return self._client_data or self.load_client()

    def _require_core_metadata(self) -> dict[str, Any]:
        if self.packages_metadata is None:
            self._load_metadata_only()
        return cast(dict[str, Any], self.packages_metadata)

    def _require_client_metadata(self) -> dict[str, Any]:
        if self._client_metadata is None:
            self._load_metadata_only()
        return cast(dict[str, Any], self._client_metadata)

    def get_all_items(self) -> list[dict[str, Any]]:
        """Return the merged list of core and client governance items."""
        return cast(
            list[dict[str, Any]], self._require_core_data().get("items", [])
        ) + cast(list[dict[str, Any]], self._require_client_data().get("items", []))

    def get_items_by_type(self, item_type: str) -> list[dict[str, Any]]:
        """Return all governance items matching the requested type."""
        target = item_type.upper()
        return [
            item
            for item in self.get_all_items()
            if item.get("type", "").upper() == target
        ]

    def get_fingerprints(self) -> dict[str, str]:
        """Return the core, client, and salt fingerprints for loaded artifacts."""
        client = self._require_client_metadata()
        core = self._require_core_metadata()
        return {
            "core": str(core.get("fingerprint", "")),
            "client": str(client.get("fingerprint", "")),
            "salt": str(client.get("fingerprint_salt", "")),
        }

    def _validate_integrity(self) -> bool:
        fps = self.get_fingerprints()
        return all(
            [
                fps["core"],
                fps["client"],
                fps["core"] == fps["salt"] if fps["salt"] else True,
                fps["core"] != fps["client"],
                len(self._require_core_data().get("items", [])) > 0,
            ]
        )

    def load_all(self) -> dict[str, Any]:
        """Load all compiled artifacts and return a validated summary payload."""
        core_data = self.load_core()
        client_data = self.load_client()
        if not self._validate_integrity():
            raise RuntimeError("Governance integrity validation failed")
        return {
            "status": "loaded",
            "core_items": len(core_data.get("items", [])),
            "client_items": len(client_data.get("items", [])),
            "core_fingerprint": self._require_core_metadata().get("fingerprint"),
            "client_fingerprint": self._require_client_metadata().get("fingerprint"),
            "context_source": self._core_context_source,
        }


__all__ = ["GovernanceLoader", "TemplateGenerator", "get_sdd_paths", "resolve_profile"]
