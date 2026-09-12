from providence_runtime.policy import (
    SEVERITY_HARD,
    SEVERITY_NONE,
    SEVERITY_SOFT,
    PolicyEngine,
)


class DummyArtifact:
    def __init__(self, fingerprint="fp", schema_version="1.0", profile="master"):
        self.fingerprint = fingerprint
        self.schema_version = schema_version
        self.profile = profile


class DummySession:
    def __init__(self, artifact_fingerprint="fp"):
        self.artifact_fingerprint = artifact_fingerprint


def test_evaluate_missing_artifact_sensitive():
    engine = PolicyEngine()
    result = engine.evaluate(has_artifact=False, is_sensitive=True)
    assert not result.allowed
    assert result.severity == SEVERITY_HARD
    assert "missing_governance_artifact" in result.reason


def test_evaluate_missing_artifact_non_sensitive():
    engine = PolicyEngine()
    result = engine.evaluate(has_artifact=False, is_sensitive=False)
    assert result.allowed
    assert result.severity == SEVERITY_SOFT
    assert "non_sensitive" in result.reason


def test_evaluate_has_artifact():
    engine = PolicyEngine()
    result = engine.evaluate(has_artifact=True, is_sensitive=True)
    assert result.allowed
    assert result.severity == SEVERITY_NONE
    assert result.reason == "ok"


def test_validate_preflight_all_ok():
    engine = PolicyEngine()
    artifact = DummyArtifact()
    session = DummySession()
    result = engine.validate_preflight(
        artifact=artifact, session=session, current_profile="master"
    )
    assert result.allowed
    assert result.severity == SEVERITY_NONE
    assert result.reason == "ok"


def test_validate_preflight_missing_fingerprint():
    engine = PolicyEngine()
    artifact = DummyArtifact(fingerprint="")
    session = DummySession()
    result = engine.validate_preflight(
        artifact=artifact, session=session, current_profile="master"
    )
    assert not result.allowed
    assert result.severity == SEVERITY_HARD
    assert "missing_fingerprint" in result.reason


def test_validate_preflight_missing_schema_version():
    engine = PolicyEngine()
    artifact = DummyArtifact(schema_version="")
    session = DummySession()
    result = engine.validate_preflight(
        artifact=artifact, session=session, current_profile="master"
    )
    assert not result.allowed
    assert result.severity == SEVERITY_HARD
    assert "missing_schema_version" in result.reason


def test_validate_preflight_fingerprint_mismatch():
    engine = PolicyEngine()
    artifact = DummyArtifact(fingerprint="fp1")
    session = DummySession(artifact_fingerprint="fp2")
    result = engine.validate_preflight(
        artifact=artifact, session=session, current_profile="master"
    )
    assert not result.allowed
    assert result.severity == SEVERITY_HARD
    assert "fingerprint_mismatch" in result.reason


def test_validate_preflight_profile_mismatch():
    engine = PolicyEngine()
    artifact = DummyArtifact(profile="client")
    session = DummySession()
    result = engine.validate_preflight(
        artifact=artifact, session=session, current_profile="master"
    )
    assert not result.allowed
    assert result.severity == SEVERITY_HARD
    assert "profile_mismatch" in result.reason
