from __future__ import annotations

from providence_cli.services.ask_payload import build_ask_json_data


def test_build_ask_json_data_base_fields() -> None:
    payload = build_ask_json_data(
        profile="master",
        query_hash="abc123",
        context_source="compiled",
        fingerprint="fp-1",
        mandates_loaded=3,
        trust_source="verified",
        degraded=False,
        degraded_reason="",
        drift_detected=False,
        governance_footer="PROVIDENCE GOVERNANCE: drift=none",
        intake_index_mode="multi",
        intake_chunks=2,
        intake_retrieval="indexed_only",
        intake_artifact="/tmp/artifact.json",
    )
    assert payload["profile"] == "master"
    assert payload["query_hash"] == "abc123"
    assert payload["fingerprint"] == "fp-1"
    assert payload["governance_mode"] == "hard"
    assert payload["execution_gate"] == "allowed"
    assert payload["ahp_state"] == "UNKNOWN"
    assert payload["intake_chunks"] == 2


def test_build_ask_json_data_merges_extra_fields() -> None:
    payload = build_ask_json_data(
        profile="master",
        query_hash="abc123",
        context_source="compiled",
        fingerprint=None,
        mandates_loaded=1,
        trust_source="verified",
        degraded=True,
        degraded_reason="signature_warn",
        drift_detected=True,
        governance_footer="PROVIDENCE GOVERNANCE: drift=detected",
        intake_index_mode="none",
        intake_chunks=0,
        intake_retrieval="indexed_only",
        intake_artifact="n/a",
        full=True,
        steps=[{"step_id": "A"}],
        extra={"log_format": "jsonl"},
    )
    assert payload["fingerprint"] == "n/a"
    assert payload["degraded"] is True
    assert payload["steps"] == [{"step_id": "A"}]
    assert payload["log_format"] == "jsonl"
