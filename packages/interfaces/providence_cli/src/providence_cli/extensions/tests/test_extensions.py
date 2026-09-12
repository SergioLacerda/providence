"""Tests for SDD Extension Framework data models (mandates, guidelines, metadata)."""

from providence_cli.extensions.framework.extension_framework import (
    Category,
    CustomGuideline,
    CustomMandate,
    ExtensionMetadata,
)


class TestCustomMandate:
    """Test CustomMandate creation and validation"""

    def test_create_valid_mandate(self) -> None:
        """Test creating valid mandate"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="Test Mandate",
            description="Test description",
            category=Category.GENERAL.value,
        )

        assert mandate.id == "M001"
        assert mandate.type == "HARD"
        assert len(mandate.validate()) == 0

    def test_mandate_missing_id(self) -> None:
        """Test mandate with missing ID fails validation"""
        mandate = CustomMandate(
            id="",
            type="HARD",
            title="Test",
            description="Test",
        )

        errors = mandate.validate()
        assert any("ID" in e for e in errors)

    def test_mandate_invalid_type(self) -> None:
        """Test mandate with invalid type fails validation"""
        mandate = CustomMandate(
            id="M001",
            type="INVALID",
            title="Test",
            description="Test",
        )

        errors = mandate.validate()
        assert any("type" in e.lower() for e in errors)

    def test_mandate_missing_title(self) -> None:
        """Test mandate with missing title fails validation"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="",
            description="Test",
        )

        errors = mandate.validate()
        assert any("title" in e.lower() for e in errors)

    def test_mandate_to_dict(self) -> None:
        """Test mandate conversion to dict"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="Test",
            description="Test Description",
            category=Category.ARCHITECTURE.value,
            domain="test-domain",
        )

        d = mandate.to_dict()

        assert d["id"] == "M001"
        assert d["type"] == "HARD"
        assert d["title"] == "Test"
        assert d["domain"] == "test-domain"


class TestCustomGuideline:
    """Test CustomGuideline creation and validation"""

    def test_create_valid_guideline(self) -> None:
        """Test creating valid guideline"""
        guideline = CustomGuideline(
            id="G01",
            type="SOFT",
            title="Test Guideline",
            category=Category.GENERAL.value,
        )

        assert guideline.id == "G01"
        assert guideline.type == "SOFT"
        assert len(guideline.validate()) == 0

    def test_guideline_invalid_type(self) -> None:
        """Test guideline with invalid type fails validation"""
        guideline = CustomGuideline(
            id="G01",
            type="MAYBE",
            title="Test",
        )

        errors = guideline.validate()
        assert any("type" in e.lower() for e in errors)

    def test_guideline_to_dict(self) -> None:
        """Test guideline conversion to dict"""
        guideline = CustomGuideline(
            id="G01",
            type="SOFT",
            title="Test Guideline",
            category=Category.TESTING.value,
            domain="test-domain",
            examples=["Example 1", "Example 2"],
        )

        d = guideline.to_dict()

        assert d["id"] == "G01"
        assert d["examples"] == ["Example 1", "Example 2"]
        assert d["domain"] == "test-domain"


class TestExtensionMetadata:
    """Test ExtensionMetadata"""

    def test_create_metadata(self) -> None:
        """Test creating extension metadata"""
        meta = ExtensionMetadata(
            name="Test Extension",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            domain="test-domain",
        )

        assert meta.name == "Test Extension"
        assert meta.version == "1.0.0"
        assert meta.domain == "test-domain"

    def test_metadata_to_dict(self) -> None:
        """Test metadata conversion to dict"""
        meta = ExtensionMetadata(
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            domain="test",
            dependencies=["dep1", "dep2"],
        )

        d = meta.to_dict()

        assert d["name"] == "Test"
        assert d["dependencies"] == ["dep1", "dep2"]
