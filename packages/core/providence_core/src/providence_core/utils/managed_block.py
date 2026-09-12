"""Managed-block convention for files sdd shares with other tools/agents.

Some generated files (root `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`) use
filenames that are conventions independently recognized by other AI coding
tools — sdd does not own the whole file, only the governance content it
itself writes. This module lets a generator replace only its own delimited
region on regeneration, preserving everything else in the file exactly as
found (a human's notes, another tool's own instructions, etc.), and lets a
validator extract that same region without assuming anything about content
outside it.

See `.analysis/refined/20260906-root-seed-githook-necessity/design.md`.
"""

from __future__ import annotations

_BLOCK_BEGIN = "<!-- sdd:managed:begin -->"
_BLOCK_END = "<!-- sdd:managed:end -->"


class MalformedManagedBlockError(ValueError):
    """Raised when managed-block markers are present but unbalanced.

    Never caught to fall back to a whole-file overwrite — that would
    silently destroy whatever content the markers were protecting, which is
    exactly what this convention exists to prevent.
    """


def _find_markers(content: str) -> tuple[int, int] | None:
    """Return (begin_index, end_of_end_marker_index) or None if absent.

    Raises `MalformedManagedBlockError` if markers are unbalanced or
    duplicated (more than one begin, or a mismatched count of begin/end).
    """
    begin_count = content.count(_BLOCK_BEGIN)
    end_count = content.count(_BLOCK_END)
    if begin_count != end_count or begin_count > 1:
        raise MalformedManagedBlockError(
            f"expected 0 or 1 balanced managed-block marker pairs, "
            f"found {begin_count} begin / {end_count} end"
        )
    if begin_count == 0:
        return None
    start = content.index(_BLOCK_BEGIN)
    end = content.index(_BLOCK_END) + len(_BLOCK_END)
    return start, end


def merge_managed_block(existing_content: str | None, new_block_body: str) -> str:
    """Return the full file content with the sdd-managed block replaced.

    Args:
        existing_content: Current file content, or None for a not-yet-existing file.
        new_block_body: Freshly generated content for the block interior
            (no markers — they are added here).

    Returns:
        The full file content to write: everything outside the managed
        block is preserved byte-for-byte; the block itself (or a newly
        inserted one, if none existed) contains `new_block_body`.

    Raises:
        MalformedManagedBlockError: existing markers are unbalanced or
            duplicated. Callers must not catch this to fall back to
            overwriting the file — see the class docstring.
    """
    block = f"{_BLOCK_BEGIN}\n{new_block_body}\n{_BLOCK_END}"
    if not existing_content:
        return block + "\n"

    markers = _find_markers(existing_content)
    if markers is None:
        # No existing block: insert at the top, preserve everything else below.
        return block + "\n" + existing_content

    start, end = markers
    return existing_content[:start] + block + existing_content[end:]


def extract_managed_block(content: str) -> str | None:
    """Return the managed block's interior content, or None if absent/malformed.

    Unlike `merge_managed_block`, this never raises — a validator reading an
    arbitrary file (possibly hand-edited, possibly predating this
    convention) degrades safely to "no managed block found" rather than
    failing loudly. Malformed markers are treated the same as absent markers
    here: this function reports, it does not enforce.
    """
    try:
        markers = _find_markers(content)
    except MalformedManagedBlockError:
        return None
    if markers is None:
        return None
    start, end = markers
    return content[start + len(_BLOCK_BEGIN) : end - len(_BLOCK_END)].strip("\n")
