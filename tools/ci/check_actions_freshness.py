#!/usr/bin/env python3
"""Report GitHub Actions pinned to a SHA older than the upstream latest tag.

Used by the `ecosystem-canary` workflow's `actions-canary` job: GitHub
Actions has no lockfile or test suite to float dependencies against, so
freshness here means comparing each `uses: owner/repo@<sha>  # vX.Y.Z` pin
against the repo's own latest upstream tag, not running anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

USES_RE = re.compile(
    r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})\s*#\s*(v[0-9][^\s]*)"
)
WORKFLOW_GLOBS = (".github/workflows/**/*.yml", ".github/actions/**/action.yml")

FetchTagsFn = Callable[..., list[str]]


@dataclass(frozen=True)
class PinnedUse:
    repo: str
    sha: str
    tag: str
    file: str


@dataclass(frozen=True)
class OutdatedAction:
    repo: str
    pinned_tag: str
    latest_tag: str
    files: list[str] = field(default_factory=list)


def _parse_version(tag: str) -> tuple[int, ...] | None:
    text = tag.strip()
    if text.startswith("v"):
        text = text[1:]
    parts = text.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def _scan_pinned_uses(root: Path) -> list[PinnedUse]:
    found: list[PinnedUse] = []
    for pattern in WORKFLOW_GLOBS:
        for path in sorted(root.glob(pattern)):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(root).as_posix()
            for match in USES_RE.finditer(text):
                repo, sha, tag = match.groups()
                found.append(PinnedUse(repo=repo, sha=sha, tag=tag, file=rel))
    return found


def _fetch_tags(repo: str, *, token: str | None) -> list[str]:
    url = f"https://api.github.com/repos/{repo}/tags?per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "providence-ecosystem-canary",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
        payload = json.loads(response.read().decode("utf-8"))
    return [entry["name"] for entry in payload if isinstance(entry.get("name"), str)]


def _latest_tag(
    repo: str, *, token: str | None, fetch_tags: FetchTagsFn = _fetch_tags
) -> str | None:
    try:
        tags = fetch_tags(repo, token=token)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ValueError,
    ) as exc:
        print(f"WARN: could not fetch tags for {repo}: {exc}")
        return None

    best_tag: str | None = None
    best_version: tuple[int, ...] | None = None
    for tag in tags:
        version = _parse_version(tag)
        if version is None:
            continue
        if best_version is None or version > best_version:
            best_version = version
            best_tag = tag
    return best_tag


def _find_outdated(
    pinned: list[PinnedUse], *, token: str | None, fetch_tags: FetchTagsFn = _fetch_tags
) -> list[OutdatedAction]:
    files_by_repo_tag: dict[tuple[str, str], list[str]] = {}
    for use in pinned:
        files_by_repo_tag.setdefault((use.repo, use.tag), []).append(use.file)

    outdated: list[OutdatedAction] = []
    checked_repos: dict[str, str | None] = {}
    for (repo, pinned_tag), files in sorted(files_by_repo_tag.items()):
        if repo not in checked_repos:
            checked_repos[repo] = _latest_tag(repo, token=token, fetch_tags=fetch_tags)
        latest_tag = checked_repos[repo]
        if latest_tag is None:
            continue

        pinned_version = _parse_version(pinned_tag)
        latest_version = _parse_version(latest_tag)
        if pinned_version is None or latest_version is None:
            continue
        if latest_version > pinned_version:
            outdated.append(
                OutdatedAction(
                    repo=repo,
                    pinned_tag=pinned_tag,
                    latest_tag=latest_tag,
                    files=sorted(files),
                )
            )
    return outdated


def _format_report(outdated: list[OutdatedAction]) -> str:
    if not outdated:
        return "All pinned GitHub Actions are at their latest upstream tag."
    lines = ["Outdated GitHub Actions pins found:", ""]
    for item in outdated:
        lines.append(
            f"- {item.repo}: pinned {item.pinned_tag} -> latest {item.latest_tag}"
        )
        for f in item.files:
            lines.append(f"    used in {f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare pinned GitHub Actions SHAs against upstream latest tags."
    )
    parser.add_argument(
        "--root", default=".", help="Repository root to scan (default: cwd)"
    )
    parser.add_argument(
        "--json-out", default=None, help="Optional path to write a JSON summary"
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    pinned = _scan_pinned_uses(root)
    outdated = _find_outdated(pinned, token=token)

    print(_format_report(outdated))

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                [
                    {
                        "repo": item.repo,
                        "pinned_tag": item.pinned_tag,
                        "latest_tag": item.latest_tag,
                        "files": item.files,
                    }
                    for item in outdated
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    return 1 if outdated else 0


if __name__ == "__main__":
    raise SystemExit(main())
