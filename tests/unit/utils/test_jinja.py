"""
Tests for utils/jinja.py module.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, mock_open

from utils.jinja import get_template_with_args


class TestGetTemplateWithArgs:
    """Test get_template_with_args function."""

    @pytest.mark.asyncio
    async def test_get_template_with_args_basic(self, tmp_path):
        """Test basic template rendering."""
        # Create a test template
        template_content = "Hello {{ name }}!"
        template_path = tmp_path / "test.jinja"
        template_path.write_text(template_content)

        with patch('utils.jinja.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.read_text.return_value = template_content

            result = await get_template_with_args("test.jinja", name="World")

            assert "World" in result
            assert "Hello" in result

    @pytest.mark.asyncio
    async def test_get_template_with_args_multiple_vars(self, tmp_path):
        """Test template rendering with multiple variables."""
        template_content = "{{ greeting }} {{ name }}! You have {{ count }} messages."
        template_path = tmp_path / "test.jinja"
        template_path.write_text(template_content)

        with patch('utils.jinja.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.read_text.return_value = template_content

            result = await get_template_with_args(
                "test.jinja",
                greeting="Hello",
                name="Alice",
                count=5
            )

            assert "Hello" in result
            assert "Alice" in result
            assert "5" in result

    @pytest.mark.asyncio
    async def test_get_template_with_args_no_vars(self, tmp_path):
        """Test template rendering without variables."""
        template_content = "This is a static template."
        template_path = tmp_path / "test.jinja"
        template_path.write_text(template_content)

        with patch('utils.jinja.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.read_text.return_value = template_content

            result = await get_template_with_args("test.jinja")

            assert result == template_content

    @pytest.mark.asyncio
    async def test_get_template_with_args_loops(self, tmp_path):
        """Test template rendering with loops."""
        template_content = "{% for item in items %}{{ item }} {% endfor %}"
        template_path = tmp_path / "test.jinja"
        template_path.write_text(template_content)

        with patch('utils.jinja.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.read_text.return_value = template_content

            result = await get_template_with_args(
                "test.jinja",
                items=["apple", "banana", "cherry"]
            )

            assert "apple" in result
            assert "banana" in result
            assert "cherry" in result

    @pytest.mark.asyncio
    async def test_get_template_with_args_conditionals(self, tmp_path):
        """Test template rendering with conditionals."""
        template_content = "{% if show %}Visible{% else %}Hidden{% endif %}"
        template_path = tmp_path / "test.jinja"
        template_path.write_text(template_content)

        with patch('utils.jinja.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.read_text.return_value = template_content

            result_true = await get_template_with_args("test.jinja", show=True)
            assert "Visible" in result_true

            result_false = await get_template_with_args("test.jinja", show=False)
            assert "Hidden" in result_false
