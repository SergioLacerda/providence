"""Managed-block convention for files Providence shares with other tools/agents.

Some generated files (root `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`) use
filenames that are conventions independently recognized by other AI coding
tools — Providence does not own the whole file, only the governance content
it itself writes. This module lets a generator replace only its own
delimited region on regeneration, preserving everything else in the file
exactly as found (a human's notes, another tool's own instructions, etc.),
and lets a validator extract that same region without assuming anything
about content outside it.

See `.analysis/refined/20260906-root-seed-githook-necessity/design.md` and
`.analysis/refined/20260913-providence-seeds-entrypoint-brand-refinement/design.md`
(marker rename compatibility policy).
"""

from __future__ import annotations

# Recognized marker pairs, current first. Reads try every pair in order;
# writes always emit the first (current) pair — so a file carrying a legacy
# pair is silently upgraded to the current pair on its next regeneration.
# See docs/adr/20260913-providence-seeds-entrypoint-brand-refinement-adr.md.
_MARKER_PAIRS: tuple[tuple[str, str], ...] = (
    ("<!-- providence:managed:begin -->", "<!-- providence:managed:end -->"),
    ("<!-- sdd:managed:begin -->", "<!-- sdd:managed:end -->"),  # legacy, read-only
)
_BLOCK_BEGIN, _BLOCK_END = _MARKER_PAIRS[0]


class MalformedManagedBlockError(ValueError):
    """Raised when managed-block markers are present but unbalanced.

    Never caught to fall back to a whole-file overwrite — that would
    silently destroy whatever content the markers were protecting, which is
    exactly what this convention exists to prevent.
    """


def _find_markers(content: str) -> tuple[int, int, str, str] | None:
    """Return (begin_index, end_of_end_marker_index, begin, end) or None if absent.

    Tries every recognized marker pair (see `_MARKER_PAIRS`). Raises
    `MalformedManagedBlockError` if more than one begin or end marker is
    present (across all pairs combined), if begin/end counts do not match,
    or if a begin marker from one pair is paired with an end marker from a
    different pair. The returned `begin`/`end` are the exact marker strings
    matched, so callers can correctly strip them regardless of which pair
    (current or legacy) was found.
    """
    total_begin = sum(content.count(begin) for begin, _ in _MARKER_PAIRS)
    total_end = sum(content.count(end) for _, end in _MARKER_PAIRS)

    if total_begin != total_end or total_begin > 1:
        raise MalformedManagedBlockError(
            f"expected 0 or 1 balanced managed-block marker pairs, "
            f"found {total_begin} begin / {total_end} end"
        )
    if total_begin == 0:
        return None

    begin_pair = next(
        i for i, (begin, _) in enumerate(_MARKER_PAIRS) if begin in content
    )
    end_pair = next(i for i, (_, end) in enumerate(_MARKER_PAIRS) if end in content)
    if begin_pair != end_pair:
        raise MalformedManagedBlockError(
            "managed-block begin/end markers belong to different marker pairs"
        )

    begin, end = _MARKER_PAIRS[begin_pair]
    start = content.index(begin)
    finish = content.index(end) + len(end)
    return start, finish, begin, end


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

    start, end, _matched_begin, _matched_end = markers
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
    start, end, begin_marker, end_marker = markers
    return content[start + len(begin_marker) : end - len(end_marker)].strip("\n")
