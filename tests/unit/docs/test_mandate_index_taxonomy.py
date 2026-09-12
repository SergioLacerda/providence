"""Guard against DOC-01: mandates.md and INDEX.md silently drifting apart.

`.providence/source/mandates/mandates.md` is the canonical, generated mandate
register. `docs/spec/canonical/core/mandates/INDEX.md` only lists mandates
whose canonical document lives directly under `core/mandates/` — three
mandates (M001, M002, M006) are documented elsewhere on purpose (as a
selectable feature, or as a guide) and are explicitly cross-referenced in
INDEX.md rather than silently missing.

This test does not require every mandate to appear literally inside
INDEX.md's own table — that taxonomy split is intentional (see
`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` DOC-01's own
Ressalva). It fails when a mandate exists in the canonical register but is
accounted for *nowhere* — neither in INDEX.md's table nor its documented
cross-references — which would be silent, undetected drift.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Mandates whose canonical documentation intentionally lives outside
# core/mandates/ — see INDEX.md's own "documented elsewhere" table.
_DOCUMENTED_ELSEWHERE = {"M001", "M002", "M006"}


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def _canonical_mandate_ids() -> set[str]:
    content = _read(".providence/source/mandates/mandates.md")
    return set(re.findall(r"^## (M\d+):", content, flags=re.MULTILINE))


def _index_mandate_ids() -> set[str]:
    content = _read("docs/spec/canonical/core/mandates/INDEX.md")
    return set(re.findall(r"^\| (M\d+) \|", content, flags=re.MULTILINE))


def test_every_canonical_mandate_is_accounted_for() -> None:
    canonical_ids = _canonical_mandate_ids()
    assert canonical_ids, "expected at least one mandate in the canonical register"

    accounted_for = _index_mandate_ids() | _DOCUMENTED_ELSEWHERE
    missing = canonical_ids - accounted_for
    assert not missing, (
        f"mandate(s) {sorted(missing)} exist in "
        ".providence/source/mandates/mandates.md but are not listed in INDEX.md "
        "nor declared as documented elsewhere — either add them to INDEX.md "
        "or add them to _DOCUMENTED_ELSEWHERE with a canonical cross-reference"
    )


def test_documented_elsewhere_mandates_are_still_canonical() -> None:
    """Catches the inverse drift: a mandate removed from the canonical
    register but still carried in the elsewhere-exception list."""
    canonical_ids = _canonical_mandate_ids()
    stale = _DOCUMENTED_ELSEWHERE - canonical_ids
    assert not stale, (
        f"mandate(s) {sorted(stale)} are listed as 'documented elsewhere' but "
        "no longer exist in the canonical register — update INDEX.md and "
        "this test's _DOCUMENTED_ELSEWHERE set"
    )


def test_documented_elsewhere_cross_references_exist() -> None:
    index_content = _read("docs/spec/canonical/core/mandates/INDEX.md")
    for mandate_id in sorted(_DOCUMENTED_ELSEWHERE):
        assert mandate_id in index_content, (
            f"{mandate_id} is declared as documented elsewhere but INDEX.md "
            "no longer cross-references it"
        )
