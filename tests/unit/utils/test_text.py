"""
Tests for utils/text.py module.
"""
import pytest
from utils.text import clean_text


class TestCleanText:
    """Test cases for clean_text function."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "Hello World!"
        result = clean_text(text)
        assert result == "Hello World!"

    def test_clean_text_with_special_chars(self):
        """Test cleaning text with special characters."""
        text = "Price: $5.99 (50% off)"
        result = clean_text(text)
        assert "$" in result
        assert "%" in result
        assert "(" in result
        assert ")" in result

    def test_clean_text_removes_unwanted_chars(self):
        """Test that unwanted special characters are removed."""
        text = "Test@Product™®©"
        result = clean_text(text)
        assert "Test" in result
        assert "Product" in result
        assert "™" not in result
        assert "®" not in result
        assert "©" not in result

    def test_clean_text_preserves_allowed_chars(self):
        """Test that allowed special characters are preserved."""
        text = "Test-Product_123 $4.99 [50%] <sale>"
        result = clean_text(text)
        assert "-" in result
        assert "_" in result
        assert "$" in result
        assert "." in result
        assert "[" in result
        assert "]" in result
        assert "<" in result
        assert ">" in result

    def test_clean_text_with_unicode(self):
        """Test cleaning text with unicode characters."""
        text = "Café Jalapeño"
        result = clean_text(text)
        assert "Café" in result
        assert "Jalapeño" in result or "Jalapeo" in result  # Some unicode chars may be preserved

    def test_clean_text_empty_string(self):
        """Test cleaning empty string."""
        result = clean_text("")
        assert result is None

    def test_clean_text_none(self):
        """Test cleaning None value."""
        result = clean_text(None)
        assert result is None

    def test_clean_text_numbers(self):
        """Test cleaning text with numbers."""
        text = "Product123 12oz 2/$5"
        result = clean_text(text)
        assert "123" in result
        assert "12" in result
        assert "/" in result
        assert "$" in result

    def test_clean_text_whitespace(self):
        """Test cleaning text with various whitespace."""
        text = "Test  Product\t\nNew Line"
        result = clean_text(text)
        assert "Test" in result
        assert "Product" in result

    def test_clean_text_mixed_case(self):
        """Test cleaning text with mixed case."""
        text = "TeSt PrOdUcT"
        result = clean_text(text)
        assert "TeSt" in result
        assert "PrOdUcT" in result

    @pytest.mark.parametrize(
        "input_text,expected_chars",
        [
            ("$4.99", ["$", "4", ".", "9"]),
            ("50%", ["5", "0", "%"]),
            ("Buy 1, Get 1", ["B", "u", "y", "1", ","]),
            ("2/$5.00", ["2", "/", "$", "5"]),
            ("Test's Product", ["T", "e", "s", "t", "'", "s"]),
        ],
    )
    def test_clean_text_parametrized(self, input_text, expected_chars):
        """Parametrized test for various input patterns."""
        result = clean_text(input_text)
        for char in expected_chars:
            assert char in result, f"Expected '{char}' in result '{result}'"
