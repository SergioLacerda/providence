from __future__ import annotations

from pathlib import Path

_SELECTOR_JS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "providence_wizard"
    / "templates"
    / "selector"
    / "selector.js"
)

_BANNER_JS = Path(__file__).resolve().parents[4] / "docs" / "app" / "sdd-banner.js"


def test_selector_js_does_not_use_innerhtml() -> None:
    js = _SELECTOR_JS.read_text(encoding="utf-8")
    assert "innerHTML" not in js


def test_selector_js_renders_items_via_dom_apis() -> None:
    js = _SELECTOR_JS.read_text(encoding="utf-8")
    assert "createElement" in js
    assert "textContent" in js
    assert "replaceChildren" in js


def test_banner_js_does_not_use_innerhtml() -> None:
    if not _BANNER_JS.exists():
        return
    js = _BANNER_JS.read_text(encoding="utf-8")
    assert "innerHTML" not in js
