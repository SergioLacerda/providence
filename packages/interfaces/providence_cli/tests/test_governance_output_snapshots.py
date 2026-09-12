from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner
from tests.helpers.text_io import read_text_utf8

from providence_cli.main import app
from providence_cli.services.runtime_preflight import PreflightResult

runner = CliRunner()
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


class _FakeAHP:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root

    def is_handshake_valid(self) -> bool:
        return True


_LIGHT_BOX_CHARS = frozenset(
    "\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
)

_BORDER_NORMALIZE = str.maketrans(
    {
        "\u2501": "\u2500",
        "\u2503": "\u2502",
        "\u250f": "\u250c",
        "\u2513": "\u2510",
        "\u2517": "\u2514",
        "\u251b": "\u2518",
        "\u2521": "\u251c",
        "\u2529": "\u2524",
        "\u2533": "\u252c",
        "\u253b": "\u2534",
        "\u2547": "\u253c",
        "\u2550": "\u2500",
        "\u2551": "\u2502",
        "\u2554": "\u250c",
        "\u2557": "\u2510",
        "\u255a": "\u2514",
        "\u255d": "\u2518",
        "\u2560": "\u251c",
        "\u2563": "\u2524",
        "\u2566": "\u252c",
        "\u2569": "\u2534",
        "\u256c": "\u253c",
        "\u256d": "\u250c",
        "\u256e": "\u2510",
        "\u2570": "\u2514",
        "\u256f": "\u2518",
    }
)


def _normalize_snapshot_text(text: str) -> str:
    # 1. Normalize box-drawing char variants to light equivalents.
    normalized = text.translate(_BORDER_NORMALIZE)
    horizontal = "\u2500"
    vertical = "\u2502"
    # 2. Collapse runs of horizontal borders to a single sentinel.
    normalized = re.sub(f"{horizontal}{{2,}}", horizontal, normalized)
    # 3. Strip padding spaces before closing box vertical chars on content lines
    #    (| text         |). The padding is terminal-width-dependent.
    normalized = re.sub(f" +({vertical})", r"\1", normalized)
    # 4. Normalize centered/plain heading lines outside box borders. Rich may
    #    center table titles with variable left padding depending on console width.
    lines: list[str] = []
    for line in normalized.splitlines():
        if not any(ch in _LIGHT_BOX_CHARS for ch in line):
            lines.append(line.strip())
        else:
            lines.append(line.rstrip())
    # 5. Strip overall trailing content.
    return "\n".join(lines).rstrip()


def _assert_snapshot(name: str, actual: str) -> None:
    expected = read_text_utf8(SNAPSHOT_DIR / name)
    assert _normalize_snapshot_text(actual) == _normalize_snapshot_text(expected)


def test_border_normalize_covers_all_snapshot_chars() -> None:
    """Every non-light box-drawing char in committed snapshots must be in _BORDER_NORMALIZE.

    Fails if a new snapshot introduces a heavy/arc/mixed variant that the normalizer
    does not map to a light equivalent, which would cause cross-platform mismatches.
    """
    uncovered: list[str] = []
    for snap_file in sorted(SNAPSHOT_DIR.glob("*.txt")):
        for ch in read_text_utf8(snap_file):
            code = ord(ch)
            if 0x2500 <= code <= 0x257F and ch not in _LIGHT_BOX_CHARS:
                translated = ch.translate(_BORDER_NORMALIZE)
                if translated not in _LIGHT_BOX_CHARS:
                    uncovered.append(
                        f"{snap_file.name}: U+{code:04X} {ch!r} not normalized"
                    )
    assert not uncovered, (
        "Snapshot contains box-drawing chars not covered by _BORDER_NORMALIZE:\n"
        + "\n".join(f"  {item}" for item in uncovered)
        + "\nAdd the missing mapping to _BORDER_NORMALIZE."
    )


def test_governance_compile_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.run_compilation",
        lambda profile=None, *, console: {
            "full_pipeline_success": True,
            "phase_1": {
                "core_item_count": 3,
                "client_item_count": 5,
                "core_fingerprint": "abc123",
            },
            "phase_2": {
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
        },
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.update_profile_hash",
        lambda _, *, console: None,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.emit_compile_telemetry",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.regenerate_seeds",
        lambda *, console: None,
    )
    result = runner.invoke(app, ["governance", "compile"])
    assert result.exit_code == 0, result.output
    _assert_snapshot("governance_compile.txt", result.output)


def test_governance_load_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config", lambda _: {}
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.get_governance_summary",
        lambda p, config=None: {"items": 8, "profile": "client"},
    )
    result = runner.invoke(app, ["governance", "load", "--path", "runtime"])
    assert result.exit_code == 0, result.output
    _assert_snapshot("governance_load.txt", result.output)


def test_governance_validate_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_files_accessible",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_fingerprints_valid",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_root_seed_drift",
        lambda _: (True, "no root-seed drift detected"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_preflight.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={}),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_validate_handlers._build_language_governance_advisories",
        lambda **_: [],
    )
    result = runner.invoke(app, ["governance", "validate", "--path", "runtime"])
    assert result.exit_code == 0, result.output
    _assert_snapshot("governance_validate.txt", result.output)
