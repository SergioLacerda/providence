from __future__ import annotations

from pathlib import Path

from providence_runtime._skill_executor._executor_footer import resolve_footer_policy


def test_resolve_footer_policy_reads_runtime_state(tmp_path: Path) -> None:
    state_dir = tmp_path / ".providence" / "runtime"
    state_dir.mkdir(parents=True)
    (state_dir / "governance-state.json").write_text(
        '{"response_footer_policy":"always"}', encoding="utf-8"
    )
    assert resolve_footer_policy(tmp_path) == "always"


def test_resolve_footer_policy_falls_back_to_always_on_invalid_json(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".providence" / "runtime"
    state_dir.mkdir(parents=True)
    (state_dir / "governance-state.json").write_text("{invalid", encoding="utf-8")
    assert resolve_footer_policy(tmp_path) == "always"
