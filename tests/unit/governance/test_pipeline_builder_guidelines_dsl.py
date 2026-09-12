from pathlib import Path

import pytest

from providence_integration.builders.governance.pipeline_builder import PipelineBuilder

pytestmark = pytest.mark.unit


def test_pipeline_builder_parses_compact_guidelines_dsl(tmp_path: Path) -> None:
    """Ensure compact `G01: ...` guidelines format generates client items."""
    (tmp_path / "mandate.md").write_text(
        "# M001: Clean Architecture\n", encoding="utf-8"
    )
    (tmp_path / "guidelines.dsl").write_text(
        "\n".join(
            [
                "G01: Constitution Customization Guide",
                "Title: Guide",
                "Type: GUIDELINE",
                "",
                "G02: When to Customize",
                "Title: Customize",
                "Type: GUIDELINE",
            ]
        ),
        encoding="utf-8",
    )

    result = PipelineBuilder(str(tmp_path)).build()

    client_ids = [item["id"] for item in result["client_items"]]
    assert client_ids == ["G01", "G02"]


def test_pipeline_builder_parses_block_guidelines_with_title_description(
    tmp_path: Path,
) -> None:
    (tmp_path / "mandate.md").write_text(
        "# M001: Clean Architecture\n", encoding="utf-8"
    )
    (tmp_path / "guidelines.dsl").write_text(
        """
guideline G002 {
  title: "Prefer small functions"
  description: "Keep functions focused and cohesive."
}
guideline G001 {
  title: "Use dependency injection"
  description: "Inject collaborators instead of globals."
}
""".strip(),
        encoding="utf-8",
    )

    result = PipelineBuilder(str(tmp_path)).build()
    client_items = result["client_items"]
    assert [item["id"] for item in client_items] == ["G001", "G002"]
    assert client_items[0]["title"] == "Use dependency injection"
    assert client_items[0]["description"] == "Inject collaborators instead of globals."
    assert client_items[1]["title"] == "Prefer small functions"
    assert client_items[1]["description"] == "Keep functions focused and cohesive."


def test_pipeline_builder_guideline_title_fallbacks_to_id_when_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "mandate.md").write_text(
        "# M001: Clean Architecture\n", encoding="utf-8"
    )
    (tmp_path / "guidelines.dsl").write_text(
        """
guideline G001 {
  description: "No explicit title in this block."
}
""".strip(),
        encoding="utf-8",
    )

    result = PipelineBuilder(str(tmp_path)).build()
    guideline = result["client_items"][0]
    assert guideline["id"] == "G001"
    assert guideline["title"] == "G001"
    assert guideline["description"] == "No explicit title in this block."
