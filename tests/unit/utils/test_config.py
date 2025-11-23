"""
Tests for utils/config.py module.
"""
import configparser
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from utils.config import get_config


class TestGetConfig:
    """Test cases for get_config function."""

    def test_get_config_file_exists(self, temp_config_file, monkeypatch):
        """Test get_config when config.ini exists."""
        # Change to temp directory
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        assert isinstance(config, configparser.ConfigParser)
        assert 'config' in config.sections()
        assert config['config']['GOOGLE_API_KEY'] == 'test-api-key'

    def test_get_config_file_missing(self, tmp_path, monkeypatch):
        """Test get_config raises exception when config.ini is missing."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(Exception, match="config.ini not found"):
            get_config()

    def test_get_config_has_required_sections(self, temp_config_file, monkeypatch):
        """Test that config has required sections."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        assert 'config' in config.sections()
        assert 'test-store' in config.sections()
        assert 'directions' in config.sections()

    def test_get_config_reads_all_values(self, temp_config_file, monkeypatch):
        """Test that all config values are read correctly."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()

        # Test config section
        assert config['config']['GOOGLE_API_KEY'] == 'test-api-key'
        assert config['config']['items_at_once'] == '5'
        assert config['config']['MODEL_NAME'] == 'gemini-1.0-pro-001'

        # Test store section
        assert config['test-store']['store_code'] == 'TEST123'
        assert config['test-store']['access_token'] == 'test-token'

        # Test directions section
        assert config['directions']['api_key'] == 'test-ors-key'

    def test_get_config_returns_parser(self, temp_config_file, monkeypatch):
        """Test that get_config returns a ConfigParser instance."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        assert isinstance(config, configparser.ConfigParser)

    def test_get_config_can_get_values(self, temp_config_file, monkeypatch):
        """Test that config values can be accessed using get method."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        assert config.get('config', 'GOOGLE_API_KEY') == 'test-api-key'
        assert config.get('config', 'items_at_once') == '5'

    def test_get_config_can_use_getint(self, temp_config_file, monkeypatch):
        """Test that config values can be accessed as integers."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        items = config.getint('config', 'items_at_once')
        assert isinstance(items, int)
        assert items == 5

    def test_get_config_can_use_getfloat(self, temp_config_file, monkeypatch):
        """Test that config values can be accessed as floats."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config = get_config()
        temp = config.getfloat('config', 'MODEL_TEMP')
        assert isinstance(temp, float)
        assert temp == 1.0

    def test_get_config_with_malformed_file(self, tmp_path, monkeypatch):
        """Test get_config with a malformed config file."""
        monkeypatch.chdir(tmp_path)

        # Create a malformed config file
        config_path = tmp_path / 'config.ini'
        with open(config_path, 'w') as f:
            f.write("This is not valid INI format\n")
            f.write("Random text without sections\n")

        # Should not raise an exception, but sections will be empty
        config = get_config()
        assert isinstance(config, configparser.ConfigParser)

    def test_get_config_with_empty_file(self, tmp_path, monkeypatch):
        """Test get_config with an empty config file."""
        monkeypatch.chdir(tmp_path)

        # Create an empty config file
        config_path = tmp_path / 'config.ini'
        config_path.touch()

        config = get_config()
        assert isinstance(config, configparser.ConfigParser)
        assert len(config.sections()) == 0

    def test_get_config_multiple_calls(self, temp_config_file, monkeypatch):
        """Test that multiple calls to get_config work correctly."""
        test_dir = temp_config_file.parent
        monkeypatch.chdir(test_dir)

        config1 = get_config()
        config2 = get_config()

        # Both should be valid ConfigParser instances
        assert isinstance(config1, configparser.ConfigParser)
        assert isinstance(config2, configparser.ConfigParser)

        # Both should have the same values
        assert config1['config']['GOOGLE_API_KEY'] == config2['config']['GOOGLE_API_KEY']
