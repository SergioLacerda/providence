"""CompressContextHandler — summarize and archive non-critical context."""

from __future__ import annotations

from typing import Any

from .._base import Handler, PreRunOutcome
from .._constants import _FooterFn
from .._context_builders import (
    _archive_context_candidates,
    _compress_context,
    _resolve_project_root_from_context,
)


class CompressContextHandler(Handler):
    """Summarize non-critical context and archive large candidates.

    Example:
        Long chat logs or large collections are summarized in memory and
        archived under `.providence/runtime/context-archive/<timestamp>/`.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, skill, profile, footer_fn
        project_root = _resolve_project_root_from_context(context)
        compressed_context, compression_report = _compress_context(context)
        archive_report = _archive_context_candidates(
            project_root=project_root,
            context=context,
            archival_candidates=list(compression_report.get("archival_candidates", [])),
        )
        compression_report.update(archive_report)
        return PreRunOutcome(
            artifacts={
                "compressed_context": compressed_context,
                "compression_report": compression_report,
            }
        )
