"""Pre-flight schema validation for a user-supplied custom governance JSON file.

Scenario B (see wizard-bootstrap-two-scenarios-20260705 design): instead of
generating a fresh mandates/guidelines set from markdown templates (Phase
1-3), the user supplies their own hand-edited JSON file. This module checks
that file's item-level schema *before* compilation  distinct in scope from
`providence governance validate`, which only validates already-compiled artifact
directories (fingerprint/conflict checks), never a raw pre-compilation
source file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ACCEPTED_TYPES = {"MANDATE", "GUIDELINE"}
_REQUIRED_KEYS = ("id", "type", "title")


def _validate_item(index: int, item: Any, seen_ids: set[str]) -> list[str]:
    """Validate a single governance item and register its id in `seen_ids`."""
    if not isinstance(item, dict):
        return [f"items[{index}]: expected an object, got {type(item).__name__}"]

    errors: list[str] = []

    missing = [key for key in _REQUIRED_KEYS if not item.get(key)]
    if missing:
        return [f"items[{index}]: missing required key(s): {', '.join(missing)}"]

    item_type = str(item["type"]).strip().upper()
    if item_type not in _ACCEPTED_TYPES:
        errors.append(
            f"items[{index}] (id={item['id']!r}): type must be one of "
            f"{sorted(_ACCEPTED_TYPES)}, got {item['type']!r}"
        )

    item_id = str(item["id"]).strip()
    if item_id in seen_ids:
        errors.append(f"items[{index}]: duplicate id {item_id!r}")
    seen_ids.add(item_id)

    return errors


def validate_custom_governance_file(path: Path) -> tuple[bool, list[str]]:
    """Validate a user-supplied mandates/guidelines JSON file.

    Returns (True, []) if the file is well-formed and usable, or
    (False, [human-readable errors]) otherwise. Never raises  all failure
    modes (missing file, bad JSON, bad schema) are reported as errors.
    """
    if not path.exists():
        return False, [f"custom governance file not found: {path}"]

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [f"could not read {path}: {exc}"]

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, [f"{path} is not valid JSON: {exc}"]

    if not isinstance(data, dict):
        return False, [f"{path}: top-level JSON value must be an object"]

    items = data.get("items")
    if not isinstance(items, list):
        return False, [f'{path}: missing or invalid top-level "items" array']

    if not items:
        return False, [f'{path}: "items" array is empty  at least one item is required']

    seen_ids: set[str] = set()
    errors: list[str] = []
    for index, item in enumerate(items):
        errors.extend(_validate_item(index, item, seen_ids))

    return (not errors, errors)


def load_custom_governance_file(
    custom_path: Path, output_base: Path
) -> tuple[bool, list[str]]:
    """Validate and stage a custom governance file for Phase 4-6 to consume.

    On success, writes the (already-validated) JSON to
    `output_base/.providence/source/governance-core.json`  one of the candidate
    paths `_resolve_governance_inputs` (`_phase456_governance_io.py`) already
    checks, so Phase 4's `GovernanceLoader` picks it up with zero changes to
    Phase 4-6 code. This is what lets Scenario B skip Phase 1-3 (markdown
    generation/staging/compilation) entirely: the user's file already IS the
    compiled-shape JSON those phases would otherwise produce.
    """
    ok, errors = validate_custom_governance_file(custom_path)
    if not ok:
        return False, errors

    try:
        data = json.loads(custom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"could not re-read validated file {custom_path}: {exc}"]

    target = output_base / ".providence" / "source" / "governance-core.json"
    try:
        # Incidentally creates output_base (client_compiled_dir) itself when
        # it doesn't yet exist  this is what lets PhaseFourRuntime's
        # client_compiled_dir.exists() precheck pass for Scenario B, even
        # though Phase 3 never ran.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        return False, [f"could not stage custom governance file to {target}: {exc}"]

    return True, []
