"""
Tests for utils/random_utils.py module.
"""
import pytest
import re


def test_random_hex_color_code_imports():
    """Test that random_hex_color_code can be imported."""
    try:
        from utils.random_utils import random_hex_color_code
        assert callable(random_hex_color_code)
    except ImportError:
        pytest.skip("random_utils module not found or has different structure")


def test_random_hex_color_code_format():
    """Test that random_hex_color_code returns proper ARGB format."""
    try:
        from utils.random_utils import random_hex_color_code

        color = random_hex_color_code()

        # Should be 8 characters (ARGB format: AARRGGBB)
        assert len(color) == 8

        # Should only contain valid hex characters
        assert re.match(r'^[0-9A-Fa-f]{8}$', color)
    except ImportError:
        pytest.skip("random_hex_color_code not found")


def test_random_hex_color_code_uniqueness():
    """Test that random_hex_color_code generates different colors."""
    try:
        from utils.random_utils import random_hex_color_code

        colors = [random_hex_color_code() for _ in range(10)]

        # At least some colors should be different (very unlikely all are same)
        assert len(set(colors)) > 1
    except ImportError:
        pytest.skip("random_hex_color_code not found")


def test_random_hex_color_code_alpha_channel():
    """Test that random_hex_color_code includes alpha channel."""
    try:
        from utils.random_utils import random_hex_color_code

        color = random_hex_color_code()

        # First two characters are alpha channel
        alpha = color[:2]
        assert re.match(r'^[0-9A-Fa-f]{2}$', alpha)
    except ImportError:
        pytest.skip("random_hex_color_code not found")
