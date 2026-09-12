"""Handshake cache management and persistence."""

from __future__ import annotations

import configparser
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


class HandshakeCache:
    """Manage persisted handshake cache state and related derived metadata."""

    _TTL_CLIENT_MINUTES = 30
    _TTL_MASTER_MINUTES = 480

    def __init__(
        self,
        cache_file: Path,
        cache_dir: Path,
        cache_ttl: timedelta,
        project_root: Path,
        agent_id: str,
    ) -> None:
        self.cache_file = cache_file
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.project_root = project_root
        self.agent_id = agent_id
        self.mandates_loaded: list[str] = []
        self.spec_fingerprint = ""
        self.gap_status = ""
        self.skill_profile = "default"

    def load_cache(self) -> dict[str, Any] | None:
        """Load a still-valid cached handshake report from disk."""
        if not self.cache_file.exists():
            return None
        try:
            cache = cast(
                dict[str, Any], json.loads(self.cache_file.read_text(encoding="utf-8"))
            )
            if cache.get("state") == "NOT_CONNECTED":
                return None
            last_check = datetime.fromisoformat(cache.get("last_check", ""))
            return cache if (datetime.now() - last_check) < self.cache_ttl else None
        except Exception as exc:
            logger.warning("Failed to load AHP cache: %s", exc)
            return None

    def extract_governance_core(self) -> dict[str, Any] | None:
        """Load the compiled governance core artifact when available."""
        candidate = (
            self.project_root / ".providence" / "compiled" / "governance-core.json"
        )
        if not candidate.exists():
            return None
        try:
            return cast(
                dict[str, Any], json.loads(candidate.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            logger.warning(
                "Failed to load governance-core.json at %s: %s", candidate, exc
            )
            return None

    def extract_mandates(self) -> list[str]:
        """Extract mandate identifiers from the compiled governance artifact."""
        governance_core = self.extract_governance_core() or {}
        return sorted(
            item["id"]
            for item in governance_core.get("items", [])
            if (
                item.get("type") == "MANDATE"
                or item.get("metadata", {}).get("type") == "MANDATE"
            )
            and "id" in item
        )

    def compute_spec_fingerprint(self) -> str:
        """Compute a stable governance fingerprint for cache comparisons.

        Fingerprint domain (SEC-08,
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
        purpose=governance-version identity for cache/handshake comparisons,
        algorithm=sha256, normalization=sorted-key JSON of the compiled
        governance-core artifact with `_signature`/`fingerprint` keys
        stripped, length=16-char truncated hex. This is a distinct domain
        from `GovernanceFingerprinter.generate`'s full 64-char integrity
        digest and from `ask_context_drift.compute_routing_signature`'s
        16-char cache key — matching length alone does not make two hashes
        comparable. See DRF-02 for a concrete historical bug caused by
        comparing this fingerprint's sibling (`spec_fingerprint`, hashed
        from *source* files) against a *compiled*-artifact hash.
        """
        governance_core = self.extract_governance_core()
        if not governance_core:
            return ""
        try:
            clean = {
                k: v
                for k, v in governance_core.items()
                if k not in {"_signature", "fingerprint"}
            }
            return hashlib.sha256(
                json.dumps(clean, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()[:16]
        except Exception as exc:
            logger.warning("Failed to compute spec fingerprint: %s", exc)
            return ""

    def map_ahp_to_gap(self, ahp_state: str, confidence: float) -> str:
        """Map handshake state into the legacy governance gap status model."""
        if ahp_state == "HEALTHY":
            return "ACTIVE"
        return "PARTIAL" if ahp_state == "PARTIAL" else "NOT_ACTIVE"

    def save_cache(
        self,
        state: str,
        checks: list[dict[str, Any]],
        confidence: float,
        skill_profile: str,
    ) -> None:
        """Persist a fresh handshake cache snapshot to disk."""
        if state == "NOT_CONNECTED":
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.mandates_loaded = self.extract_mandates()
            self.spec_fingerprint = self.compute_spec_fingerprint()
            self.gap_status = self.map_ahp_to_gap(state, confidence)
            self.skill_profile = skill_profile
            cache = {
                "gap_version": "1.0",
                "status": self.gap_status,
                "agent_id": self.agent_id,
                "spec_fingerprint": self.spec_fingerprint,
                "mandates_loaded": self.mandates_loaded,
                "skill_profile": skill_profile,
                "confidence": round(confidence, 1),
                "last_check": datetime.now().isoformat(),
                "state": state,
                "checks": checks,
            }
            if self.cache_file.exists():
                try:
                    cache.update(
                        {
                            key: value
                            for key, value in json.loads(
                                self.cache_file.read_text(encoding="utf-8")
                            ).items()
                            if key not in cache
                        }
                    )
                except Exception:
                    logger.debug(
                        "Could not merge existing AHP cache state", exc_info=True
                    )
            self.cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save AHP cache: %s", exc)

    def extract_skill_profile(self) -> str:
        """Read the active SDD profile type used by the workspace."""
        try:
            profile_path = self.project_root / ".providence" / "profile"
            if not profile_path.exists():
                return "default"
            parser = configparser.ConfigParser()
            parser.read(profile_path)
            profile_type = parser.get("sdd", "type", fallback="").strip().lower()
            return profile_type or "default"
        except Exception:
            return "default"

    def resolve_ttl_minutes(self) -> int:
        """Resolve cache TTL minutes from config, profile, or defaults."""
        try:
            pyproject_path = self.project_root / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
                providence_runtime = (
                    config.get("tool", {}).get("sdd", {}).get("runtime", {})
                )
                if "handshake_ttl_minutes" in providence_runtime:
                    return int(providence_runtime["handshake_ttl_minutes"])
        except (OSError, ValueError, KeyError, TypeError, ImportError):
            logger.debug(
                "Could not parse handshake_ttl_minutes from pyproject.toml",
                exc_info=True,
            )
        try:
            profile_path = self.project_root / ".providence" / "profile"
            if profile_path.exists():
                parser = configparser.ConfigParser()
                parser.read(profile_path)
                if parser.get("sdd", "type", fallback="").strip().lower() == "master":
                    return self._TTL_MASTER_MINUTES
        except Exception:
            logger.debug("Could not read workspace profile for TTL", exc_info=True)
        return self._TTL_CLIENT_MINUTES
