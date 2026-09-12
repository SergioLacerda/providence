"""Tests for group_by_category utility."""

from dataclasses import dataclass

from providence_wizard.orchestration.wizard.category_grouper import group_by_category


@dataclass
class _Item:
    id: str
    category: str


class TestGroupByCategory:
    def test_groups_by_category(self) -> None:
        items = [_Item("A", "x"), _Item("B", "y"), _Item("C", "x")]
        result = group_by_category(items)
        assert set(result.keys()) == {"x", "y"}
        assert len(result["x"]) == 2
        assert len(result["y"]) == 1

    def test_empty_returns_empty_dict(self) -> None:
        assert group_by_category([]) == {}

    def test_custom_category_attr(self) -> None:
        @dataclass
        class Tagged:
            name: str
            tag: str

        items = [Tagged("a", "foo"), Tagged("b", "bar"), Tagged("c", "foo")]
        result = group_by_category(items, category_attr="tag")
        assert len(result["foo"]) == 2
        assert len(result["bar"]) == 1

    def test_missing_attr_falls_back_to_general(self) -> None:
        class NoCategory:
            pass

        items = [NoCategory(), NoCategory()]
        result = group_by_category(items)
        assert "general" in result
        assert len(result["general"]) == 2
