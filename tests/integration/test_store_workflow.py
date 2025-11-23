"""
Integration tests for complete store workflows.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_workflow_basic(mock_config, mock_timer_cm, monkeypatch, tmp_path):
    """Test basic store workflow from initialization to data processing."""
    monkeypatch.chdir(tmp_path)
    os.makedirs('output', exist_ok=True)

    with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
        from stores.lib.BaseStore import Store

        class TestStore(Store):
            _store_name = 'test-store'

        store = TestStore(mock_timer_cm)

        # Test initialization
        assert store._store_name == 'test-store'
        assert store.store_config is not None

        # Test worksheet reset
        store.reset_worksheet()
        assert Path(store.excel_file_path).exists()

        # Test adding data
        sample_data = {
            'brand_name': 'Test',
            'product_name': 'Product',
            'price': 5.99,
        }
        store.add_row_to_store_worksheet(sample_data)

        # Test cleaning
        store.clean_worksheet()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flipp_store_workflow(mock_config, mock_timer_cm, monkeypatch, tmp_path):
    """Test Flipp store workflow."""
    monkeypatch.chdir(tmp_path)

    with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
        from stores.Flipp.Flipp import Flipp

        class TestFlippStore(Flipp):
            _store_name = 'test-store'

        store = TestFlippStore(mock_timer_cm)

        # Test properties
        assert store.store_code == 'TEST123'
        assert store.access_token == 'test-token'

        # Test URL generation
        url = store.flyer_url
        assert 'flippenterprise.net' in url
