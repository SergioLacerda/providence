"""Contract tests for governance-core compiled artifacts.

Golden-file strategy: `fixtures/governance_core.golden.json` is the canonical
reference. The test reads the live compiled artifact, strips volatile fields
(fingerprint, generated_at), and diffs the result against the golden file.

To update golden-file snapshots:
    make update-golden-snapshots
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

from providence_cli.utils.providence_authority import compiled_active_dir
from tests.helpers.text_io import read_text_utf8

REPO_ROOT = Path(__file__).parent.parent.parent
_REPO_CANONICAL_ARTIFACT = (
    REPO_ROOT / ".providence" / "compiled" / "governance-core.json"
)
_CANONICAL_ARTIFACT = compiled_active_dir() / "governance-core.json"
_LEGACY_ARTIFACT = (
    REPO_ROOT / "generated" / "master" / "compiled" / "governance-core.json"
)
GOLDEN = Path(__file__).parent / "fixtures" / "governance_core.golden.json"

_REPO_CLIENT_ARTIFACT = (
    REPO_ROOT / ".providence" / "compiled" / "governance-client.json"
)
_CLIENT_ARTIFACT = compiled_active_dir() / "governance-client.json"
_CLIENT_GOLDEN = Path(__file__).parent / "fixtures" / "governance_client.golden.json"

_VOLATILE_KEYS = frozenset({"fingerprint", "generated_at"})
_CLIENT_VOLATILE_KEYS = _VOLATILE_KEYS | {"fingerprint_core_salt"}
_ITEM_ID_PATTERN = re.compile(r"^[A-Z]\d{2,3}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _normalise(
    d: dict[str, Any],
    volatile_keys: frozenset[str] = _VOLATILE_KEYS,
) -> dict[str, Any]:
    """Remove volatile fields, sort items by ID, and sort keys for deterministic comparison."""
    clean = {k: v for k, v in d.items() if k not in volatile_keys}
    if "items" in clean and isinstance(clean["items"], list):
        clean["items"] = sorted(clean["items"], key=lambda x: x.get("id", ""))
    return cast(dict[str, Any], json.loads(json.dumps(clean, sort_keys=True)))


def _artifact_path() -> Path:
    """Resolve the compiled artifact after session fixtures have run."""
    if _REPO_CANONICAL_ARTIFACT.exists():
        return _REPO_CANONICAL_ARTIFACT
    if _CANONICAL_ARTIFACT.exists():
        return _CANONICAL_ARTIFACT
    return _LEGACY_ARTIFACT


def _client_artifact_path() -> Path:
    """Resolve the compiled client artifact after session fixtures have run."""
    if _REPO_CLIENT_ARTIFACT.exists():
        return _REPO_CLIENT_ARTIFACT
    return _CLIENT_ARTIFACT


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    """Load the compiled governance artifact once per module."""
    artifact_path = _artifact_path()
    if not artifact_path.exists():
        pytest.skip(
            f"Compiled artifact not found: {artifact_path}\n"
            "Run: uv run providence governance compile"
        )
    return json.loads(read_text_utf8(artifact_path))  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Schema invariants
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestGovernanceCoreSchema:
    """Structural invariants that must always hold for governance-core.json.

    These are the MUST requirements — the minimum contract for any consumer
    of this artifact. Flexible properties (metadata, titles) are not enforced
    here; they are covered by the golden-file regression test.
    """

    def test_artifact_exists(self) -> None:
        """MUST: Compiled artifact is present and readable."""
        artifact_path = _artifact_path()
        assert artifact_path.exists(), (
            f"Artifact missing: {artifact_path}\nRun: uv run providence governance compile"
        )

    def test_top_level_structure(self, artifact: dict[str, Any]) -> None:
        """MUST: Top-level keys include category, version, fingerprint, items."""
        required = ("category", "version", "fingerprint", "items")
        missing = [k for k in required if k not in artifact]
        assert not missing, f"Missing required fields: {missing}"
        assert isinstance(artifact["items"], list), "'items' must be a list"

    def test_category_is_core(self, artifact: dict[str, Any]) -> None:
        """MUST: Category identifies this as CORE governance."""
        assert artifact["category"] == "CORE", (
            f"Expected category='CORE', got {artifact['category']!r}"
        )

    def test_items_non_empty(self, artifact: dict[str, Any]) -> None:
        """MUST: Artifact contains at least one governance item."""
        assert len(artifact["items"]) > 0, "Artifact has no items"

    def test_all_items_have_stable_id(self, artifact: dict[str, Any]) -> None:
        """MUST: Every item has a stable ID — the primary key for linking."""
        missing = [i for i, item in enumerate(artifact["items"]) if not item.get("id")]
        assert not missing, f"Items at index {missing} are missing 'id'"

    def test_item_ids_match_pattern(self, artifact: dict[str, Any]) -> None:
        """MUST: Item IDs follow pattern [A-Z]NN or [A-Z]NNN (e.g., G01, M001)."""
        bad = [
            item.get("id")
            for item in artifact["items"]
            if not _ITEM_ID_PATTERN.match(str(item.get("id", "")))
        ]
        assert not bad, f"IDs do not match [A-Z]\\d{{2,3}}: {bad}"

    def test_fingerprint_is_valid_hash(self, artifact: dict[str, Any]) -> None:
        """MUST: Fingerprint is a valid SHA-256 hex string."""
        fp = artifact.get("fingerprint", "")
        assert _FINGERPRINT_PATTERN.match(fp), f"Not a valid SHA-256 hex string: {fp!r}"

    def test_version_present(self, artifact: dict[str, Any]) -> None:
        """MUST: Version field is present for compatibility tracking."""
        version = artifact.get("version")
        assert version, f"Missing 'version' field (got {version!r})"

    def test_artifact_validates_pydantic_schema(self, artifact: dict[str, Any]) -> None:
        """MUST: Live artifact passes Pydantic contract model validation."""
        from pydantic import ValidationError

        from tests.contract.models import GovernanceCoreArtifact

        try:
            GovernanceCoreArtifact.model_validate(artifact)
        except ValidationError as exc:
            pytest.fail(f"Artifact failed Pydantic validation:\n{exc}")

    def test_committed_schema_matches_model(self) -> None:
        """MUST: Committed schema.json matches model_json_schema() — no schema drift."""
        from tests.contract.models import GovernanceCoreArtifact

        schema_path = Path(__file__).parent / "schemas" / "governance_core.schema.json"
        if not schema_path.exists():
            pytest.fail(
                f"Schema file missing: {schema_path}\nRun: make generate-schemas"
            )
        committed = json.loads(read_text_utf8(schema_path))
        current = GovernanceCoreArtifact.model_json_schema()
        assert committed == current, (
            "Committed schema has drifted from the Pydantic model.\n"
            "Run: make generate-schemas"
        )

    @pytest.mark.slow
    def test_compilation_is_deterministic(self, artifact: dict[str, Any]) -> None:
        """MUST: Two consecutive compilations produce identical fingerprints."""
        from providence_core.governance_orchestrator import GovernanceOrchestrator

        repo_root = Path(__file__).parent.parent.parent
        GovernanceOrchestrator(repo_root=str(repo_root)).run_full_pipeline()
        second = json.loads(read_text_utf8(_artifact_path()))
        assert artifact["fingerprint"] == second["fingerprint"], (
            f"Non-deterministic compilation:\n"
            f"  first:  {artifact['fingerprint']!r}\n"
            f"  second: {second['fingerprint']!r}"
        )


# ---------------------------------------------------------------------------
# Golden-file regression guard
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.golden
class TestGovernanceCoreGoldenFile:
    """Regression guard: compiled artifact must match the committed golden snapshot.

    When compilation logic changes intentionally, update the snapshot:
        make update-golden-snapshots

    Why golden files matter:
    - Catch unintended schema drift
    - Document the evolution of governance format over time
    - Serve as reference for migration scripts
    """

    def test_golden_file_exists(self) -> None:
        """MUST: Golden fixture is present for regression testing."""
        assert GOLDEN.exists(), (
            f"Golden fixture missing: {GOLDEN}\nRun: make update-golden-snapshots"
        )

    def test_structure_matches_golden(self, artifact: dict[str, Any]) -> None:
        """Compiled artifact must match the golden snapshot (volatile fields excluded).

        On failure, review the diff:
          - Intentional change → run: make update-golden-snapshots
          - Accidental change  → investigate GovernanceOrchestrator and source docs
        """
        import difflib

        live = _normalise(artifact)
        golden = _normalise(json.loads(read_text_utf8(GOLDEN)))

        if live == golden:
            return

        live_lines = json.dumps(live, indent=2, sort_keys=True).splitlines(
            keepends=True
        )
        golden_lines = json.dumps(golden, indent=2, sort_keys=True).splitlines(
            keepends=True
        )
        diff = "".join(
            difflib.unified_diff(
                golden_lines,
                live_lines,
                fromfile="golden (expected)",
                tofile="live (actual)",
                n=4,
            )
        )

        pytest.fail(
            "Compiled artifact diverged from golden snapshot.\n\n"
            "  Intentional change?  run:      make update-golden-snapshots\n"
            "  Accidental change?   check:    GovernanceOrchestrator + source docs\n\n"
            f"--- diff (golden → live) ---\n{diff}"
        )


# ---------------------------------------------------------------------------
# Client artifact schema invariants
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client_artifact() -> dict[str, Any]:
    """Load the compiled governance client artifact once per module."""
    artifact_path = _client_artifact_path()
    if not artifact_path.exists():
        pytest.skip(
            f"Client artifact not found: {artifact_path}\n"
            "Run: uv run providence governance compile"
        )
    return json.loads(read_text_utf8(artifact_path))  # type: ignore[no-any-return]


@pytest.mark.contract
class TestGovernanceClientSchema:
    """Structural invariants for governance-client.json."""

    def test_artifact_exists(self) -> None:
        """MUST: Client artifact is present and readable."""
        artifact_path = _client_artifact_path()
        assert artifact_path.exists(), (
            f"Artifact missing: {artifact_path}\nRun: uv run providence governance compile"
        )

    def test_top_level_structure(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Top-level keys include category, version, fingerprint, items."""
        required = ("category", "version", "fingerprint", "items")
        missing = [k for k in required if k not in client_artifact]
        assert not missing, f"Missing required fields: {missing}"
        assert isinstance(client_artifact["items"], list), "'items' must be a list"

    def test_category_is_client(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Category identifies this as CLIENT governance."""
        assert client_artifact["category"] == "CLIENT", (
            f"Expected category='CLIENT', got {client_artifact['category']!r}"
        )

    def test_version_present(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Version field is present for compatibility tracking."""
        version = client_artifact.get("version")
        assert version, f"Missing 'version' field (got {version!r})"

    def test_all_items_have_stable_id(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Every item has a stable ID."""
        missing = [
            i for i, item in enumerate(client_artifact["items"]) if not item.get("id")
        ]
        assert not missing, f"Items at index {missing} are missing 'id'"

    def test_item_ids_match_pattern(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Item IDs follow pattern [A-Z]NN or [A-Z]NNN."""
        bad = [
            item.get("id")
            for item in client_artifact["items"]
            if not _ITEM_ID_PATTERN.match(str(item.get("id", "")))
        ]
        assert not bad, f"IDs do not match [A-Z]\\d{{2,3}}: {bad}"

    def test_fingerprint_is_valid_hash(self, client_artifact: dict[str, Any]) -> None:
        """MUST: Fingerprint is a valid SHA-256 hex string."""
        fp = client_artifact.get("fingerprint", "")
        assert _FINGERPRINT_PATTERN.match(fp), f"Not a valid SHA-256 hex string: {fp!r}"


# ---------------------------------------------------------------------------
# Client golden-file regression guard
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.golden
class TestGovernanceClientGoldenFile:
    """Regression guard: client artifact must match committed golden snapshot."""

    def test_golden_file_exists(self) -> None:
        """MUST: Client golden fixture is present for regression testing."""
        assert _CLIENT_GOLDEN.exists(), (
            f"Golden fixture missing: {_CLIENT_GOLDEN}\nRun: make update-golden-snapshots"
        )

    def test_structure_matches_golden(self, client_artifact: dict[str, Any]) -> None:
        """Client artifact must match the golden snapshot (volatile fields excluded).

        Skips in environments where no client-specific governance items are defined
        (e.g., CI containers where .providence/source/guidelines.dsl is gitignored).
        """
        import difflib

        if not client_artifact.get("items"):
            pytest.skip(
                "No client items in this environment — "
                "golden comparison requires a workspace with client governance specs."
            )

        live = _normalise(client_artifact, _CLIENT_VOLATILE_KEYS)
        golden = _normalise(
            json.loads(read_text_utf8(_CLIENT_GOLDEN)), _CLIENT_VOLATILE_KEYS
        )

        if live == golden:
            return

        live_lines = json.dumps(live, indent=2, sort_keys=True).splitlines(
            keepends=True
        )
        golden_lines = json.dumps(golden, indent=2, sort_keys=True).splitlines(
            keepends=True
        )
        diff = "".join(
            difflib.unified_diff(
                golden_lines,
                live_lines,
                fromfile="golden (expected)",
                tofile="live (actual)",
                n=4,
            )
        )

        pytest.fail(
            "Client artifact diverged from golden snapshot.\n\n"
            "  Intentional change?  run:      make update-golden-snapshots\n"
            "  Accidental change?   check:    GovernanceOrchestrator + source docs\n\n"
            f"--- diff (golden → live) ---\n{diff}"
        )
