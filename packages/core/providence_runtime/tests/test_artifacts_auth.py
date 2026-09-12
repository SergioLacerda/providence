from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from providence_runtime.artifacts import CompiledArtifact


def _write_core(compiled_dir: Path) -> None:
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [
                    {
                        "id": "M001",
                        "title": "t",
                        "metadata": {"type": "- mandate", "summary_runtime": "sr"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (compiled_dir / "metadata-core.json").write_text(
        json.dumps({"version": "3.0", "generated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )


def test_from_sdd_compiled_dir_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        CompiledArtifact.from_sdd_compiled_dir(tmp_path)


def test_from_governance_json_normalization_and_fallbacks(tmp_path: Path) -> None:
    _write_core(tmp_path)
    art = CompiledArtifact.from_sdd_compiled_dir(tmp_path)
    assert art.items[0].item_type == "MANDATE"
    assert art.items[0].summary_runtime == "sr"


def test_from_governance_json_roundtrip_summary_full_and_criticality(
    tmp_path: Path,
) -> None:
    """summary_full and criticality should propagate into runtime DTO."""
    items_path = tmp_path / "governance-core.json"
    items_path.write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [
                    {
                        "id": "M001",
                        "title": "t",
                        "type": "MANDATE",
                        "metadata": {
                            "summary_full": "Full explanation",
                            "criticality": "high",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    art = CompiledArtifact.from_governance_json(items_path)
    assert art.items[0].summary_full == "Full explanation"
    assert art.items[0].criticality == "high"


def test_from_governance_json_roundtrip_summary_full_and_criticality_top_level_fallback(
    tmp_path: Path,
) -> None:
    """Top-level fallback remains supported for summary_full/criticality."""
    items_path = tmp_path / "governance-core.json"
    items_path.write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [
                    {
                        "id": "M001",
                        "title": "t",
                        "type": "MANDATE",
                        "summary_full": "Top-level full",
                        "criticality": "medium",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    art = CompiledArtifact.from_governance_json(items_path)
    assert art.items[0].summary_full == "Top-level full"
    assert art.items[0].criticality == "medium"


def test_from_governance_json_prefers_top_level_type_over_legacy_metadata(
    tmp_path: Path,
) -> None:
    """Canonical top-level type must take precedence over legacy metadata.type."""
    items_path = tmp_path / "governance-core.json"
    items_path.write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [
                    {
                        "id": "M001",
                        "title": "t",
                        "type": "POLICY",
                        "metadata": {"type": "MANDATE"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    art = CompiledArtifact.from_governance_json(items_path)
    assert art.items[0].item_type == "POLICY"


def test_from_governance_json_uses_metadata_type_when_top_level_missing(
    tmp_path: Path,
) -> None:
    """Legacy metadata.type remains supported as explicit fallback."""
    items_path = tmp_path / "governance-core.json"
    items_path.write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [
                    {"id": "M001", "title": "t", "metadata": {"type": "- guideline"}}
                ],
            }
        ),
        encoding="utf-8",
    )
    art = CompiledArtifact.from_governance_json(items_path)
    assert art.items[0].item_type == "GUIDELINE"


def test_from_governance_json_defaults_unknown_when_type_absent(
    tmp_path: Path,
) -> None:
    """Items missing both type sources must default to UNKNOWN."""
    items_path = tmp_path / "governance-core.json"
    items_path.write_text(
        json.dumps(
            {
                "version": "3.0",
                "fingerprint": "fp1",
                "items": [{"id": "M001", "title": "t", "metadata": {}}],
            }
        ),
        encoding="utf-8",
    )
    art = CompiledArtifact.from_governance_json(items_path)
    assert art.items[0].item_type == "UNKNOWN"


def test_from_sdd_compiled_dir_with_auth_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_core(tmp_path)
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "off")
    result = CompiledArtifact.from_sdd_compiled_dir_with_auth(tmp_path)
    assert result.auth_state == "unverified"
    assert result.trust_source == "canonical"


@pytest.mark.asyncio
async def test_from_sdd_compiled_dir_async_matches_sync(tmp_path: Path) -> None:
    """Async variant returns same result as sync counterpart."""
    from unittest.mock import patch

    _write_core(tmp_path)
    with patch("providence_runtime.artifacts.os.environ.get", return_value="off"):
        sync_result = CompiledArtifact.from_sdd_compiled_dir(tmp_path)
        async_result = await CompiledArtifact.from_sdd_compiled_dir_async(tmp_path)

    assert async_result.fingerprint == sync_result.fingerprint
    assert len(async_result.items) == len(sync_result.items)


@pytest.mark.asyncio
async def test_from_sdd_compiled_dir_with_auth_async_returns_artifact_load_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Async with_auth variant returns an ArtifactLoadResult."""
    from providence_runtime.artifacts import ArtifactLoadResult

    _write_core(tmp_path)
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "off")
    result = await CompiledArtifact.from_sdd_compiled_dir_with_auth_async(tmp_path)
    assert isinstance(result, ArtifactLoadResult)
    assert result.artifact is not None


def test_signature_mode_default_is_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default SDD_SIGNATURE_MODE is warn — artifacts load without error but warn."""
    _write_core(tmp_path)
    monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)

    import os

    mode = os.environ.get("SDD_SIGNATURE_MODE", "warn").strip().lower()
    assert mode == "warn", f"Expected default 'warn', got '{mode}'"


def test_from_sdd_compiled_dir_with_auth_warn_degraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_core(tmp_path)
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

    class _Result:
        ok = False
        blocking = False
        code = "SIG_INVALID"
        reason = "bad"
        trust_source = "legacy"

    with patch(
        "providence_runtime.signatures.validate_artifact_signature",
        return_value=_Result(),
    ):
        result = CompiledArtifact.from_sdd_compiled_dir_with_auth(tmp_path)
        assert result.auth_state == "degraded"
        assert result.trust_source == "legacy"


def test_from_sdd_compiled_dir_with_auth_strict_blocking_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_core(tmp_path)
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")

    class _Result:
        ok = False
        blocking = True
        code = "SIG_INVALID"
        reason = "bad"
        trust_source = "none"

    with (
        patch(
            "providence_runtime.signatures.validate_artifact_signature",
            return_value=_Result(),
        ),
        pytest.raises(RuntimeError, match="SIG_INVALID"),
    ):
        CompiledArtifact.from_sdd_compiled_dir_with_auth(tmp_path)
