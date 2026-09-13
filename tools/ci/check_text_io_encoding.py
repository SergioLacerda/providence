from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOTS = ("tests", "packages", "tools")
EXCLUDED_PARTS = ("/build/lib/",)

_INGESTION_PATTERNS = ("loader", "reader", "parser", "ingest")


def _is_excluded(path: Path) -> bool:
    as_posix = path.as_posix()
    return any(part in as_posix for part in EXCLUDED_PARTS)


def _is_ingestion_file(path: Path) -> bool:
    name = path.stem.lower()
    return any(pat in name for pat in _INGESTION_PATTERNS)


def _has_encoding_kw(call: ast.Call) -> bool:
    return any(
        isinstance(k, ast.keyword) and k.arg == "encoding" for k in call.keywords
    )


def _has_errors_kw(call: ast.Call) -> bool:
    return any(isinstance(k, ast.keyword) and k.arg == "errors" for k in call.keywords)


def _is_text_open_without_encoding(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Name) or call.func.id != "open":
        return False
    if _has_encoding_kw(call):
        return False

    # Default open() mode is text ("r"), so it requires explicit encoding.
    if len(call.args) < 2:
        return True

    mode_arg = call.args[1]
    if not isinstance(mode_arg, ast.Constant) or not isinstance(mode_arg.value, str):
        # Non-literal mode: enforce explicit encoding to be safe/deterministic.
        return True

    mode = mode_arg.value
    # Binary mode is exempt from text encoding policy.
    return "b" not in mode


def _is_text_open_missing_errors(call: ast.Call) -> bool:
    """Return True for text open() with encoding= but without errors= (ingestion files only)."""
    if not isinstance(call.func, ast.Name) or call.func.id != "open":
        return False
    if not _has_encoding_kw(call):
        return False
    if _has_errors_kw(call):
        return False

    # Check it is text mode (not binary).
    if len(call.args) < 2:
        return True  # default mode is "r" (text)

    mode_arg = call.args[1]
    if not isinstance(mode_arg, ast.Constant) or not isinstance(mode_arg.value, str):
        return True  # non-literal mode: be conservative

    return "b" not in mode_arg.value


def _iter_files(repo_root: Path, paths: list[str] | None) -> list[Path]:
    if paths:
        files: list[Path] = []
        for rel in paths:
            path = (repo_root / rel).resolve()
            if (
                path.exists()
                and path.suffix == ".py"
                and path.is_file()
                and not _is_excluded(path)
            ):
                files.append(path)
        return files

    files = []
    for root_name in ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        files.extend(
            py_file for py_file in root.rglob("*.py") if not _is_excluded(py_file)
        )
    return files


def _is_fixable_missing_encoding(call: ast.Call) -> bool:
    """True for the two mechanically-fixable "no encoding=" violation shapes.

    Excludes the ingestion `errors=` advisory (semantic choice, not mechanical)
    and anything that isn't a plain `open()`/`.read_text()`/`.write_text()` call.
    """
    if _is_text_open_without_encoding(call):
        return True
    if not isinstance(call.func, ast.Attribute):
        return False
    return call.func.attr in {"read_text", "write_text"} and not _has_encoding_kw(call)


def _insert_encoding_kwarg(line: str, call: ast.Call, end_col: int) -> str | None:
    """Insert `encoding="utf-8"` just before the call's closing paren.

    `end_col` is the call's `end_col_offset` for a confirmed single-line call
    (see `_fix_file`) — passed explicitly rather than read from `call` again
    since `ast.Call.end_col_offset` is typed `int | None` in general. Returns
    None if the line doesn't look like it still has `)` where expected
    (defensive — skip rather than corrupt the file).
    """
    close_idx = end_col - 1
    if close_idx < 0 or close_idx >= len(line) or line[close_idx] != ")":
        return None
    has_args = bool(call.args) or bool(call.keywords)
    insertion = (", " if has_args else "") + 'encoding="utf-8"'
    return line[:close_idx] + insertion + line[close_idx:]


def _fix_file(py_file: Path, tree: ast.AST) -> tuple[int, int]:
    """Apply mechanical `encoding="utf-8"` fixes in place.

    Returns (fixed_count, skipped_multiline_count).
    """
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_fixable_missing_encoding(node)
    ]

    # Pair each single-line call with its (necessarily non-None) end_col_offset
    # up front, so downstream code works with a plain int, not int | None.
    single_line: list[tuple[ast.Call, int]] = []
    for call in calls:
        if call.lineno == call.end_lineno and call.end_col_offset is not None:
            single_line.append((call, call.end_col_offset))
    skipped = len(calls) - len(single_line)

    by_line: dict[int, list[tuple[ast.Call, int]]] = {}
    for call, end_col in single_line:
        by_line.setdefault(call.lineno, []).append((call, end_col))

    lines = py_file.read_text(encoding="utf-8").splitlines(keepends=True)
    fixed = 0
    for lineno, call_group in by_line.items():
        line = lines[lineno - 1]
        # Rightmost first so earlier insertions on the same line don't shift
        # the column offsets the AST computed for calls further left.
        for call, end_col in sorted(call_group, key=lambda pair: pair[1], reverse=True):
            new_line = _insert_encoding_kwarg(line, call, end_col)
            if new_line is None:
                skipped += 1
                continue
            line = new_line
            fixed += 1
        lines[lineno - 1] = line

    if fixed:
        py_file.write_text("".join(lines), encoding="utf-8")
    return fixed, skipped


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check text I/O calls enforce explicit UTF-8 encoding."
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional repository-relative Python file paths to check.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            'Mechanically insert encoding="utf-8" into single-line '
            "open()/.read_text()/.write_text() calls missing it, then "
            "re-report anything still failing (multi-line calls and the "
            "ingestion errors= advisory are never auto-fixed)."
        ),
    )
    return parser.parse_args()


def main() -> int:  # noqa: C901
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[tuple[str, str]] = []
    total_fixed = 0
    total_fix_skipped = 0

    for py_file in _iter_files(repo_root, args.paths):
        source = py_file.read_text(encoding="utf-8")
        is_ingestion = _is_ingestion_file(py_file)
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            violations.append((f"{py_file}: syntax-error while scanning ({exc})", ""))
            continue

        if args.fix:
            fixed, fix_skipped = _fix_file(py_file, tree)
            total_fixed += fixed
            total_fix_skipped += fix_skipped
            if fixed:
                # Re-read and re-parse post-fix so the report below reflects
                # what's actually still on disk, not the pre-fix tree.
                source = py_file.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(source)
                except SyntaxError as exc:  # pragma: no cover - fixer bug guard
                    violations.append(
                        (
                            f"{py_file}: syntax-error after auto-fix ({exc})",
                            "This is a bug in check_text_io_encoding.py's --fix — please report it.",
                        )
                    )
                    continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if _is_text_open_without_encoding(node):
                violations.append(
                    (
                        f"{py_file}:{node.lineno}: open() in text mode without encoding",
                        'Fix: open(path, encoding="utf-8")  or  read_text_utf8(path)',
                    )
                )
                continue

            if is_ingestion and _is_text_open_missing_errors(node):
                violations.append(
                    (
                        f"{py_file}:{node.lineno}: open() in ingestion file without errors=",
                        "Fix: add errors='strict' or errors='replace' to make decode behavior explicit",
                    )
                )
                continue

            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"read_text", "write_text"}:
                continue
            if _has_encoding_kw(node):
                continue
            violations.append(
                (
                    f"{py_file}:{node.lineno}: {node.func.attr} without encoding",
                    "Fix: use read_text_utf8(path) / write_text_utf8(path, content) from the central helper",
                )
            )

    if args.fix and (total_fixed or total_fix_skipped):
        print(
            f"Text I/O encoding auto-fix: {total_fixed} call(s) fixed, "
            f"{total_fix_skipped} skipped (multi-line calls need a manual fix)."
        )

    if violations:
        print("Text I/O encoding policy failed. Found calls without explicit encoding:")
        for msg, hint in violations:
            print(f"  - {msg}")
            if hint:
                print(f"    {hint}")
        return 1

    print("Text I/O encoding policy passed: all text I/O calls set explicit encoding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
