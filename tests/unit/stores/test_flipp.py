"""
Tests for stores/Flipp/Flipp.py module.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from stores.Flipp.Flipp import Flipp


class TestFlippInit:
    """Test Flipp class initialization."""

    def test_flipp_init_with_valid_config(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Flipp initialization with valid config."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)

            assert store.store_code == 'TEST123'
            assert store.access_token == 'test-token'

    def test_flipp_init_missing_store_code_raises_exception(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Flipp initialization raises exception for missing store_code."""
        monkeypatch.chdir(tmp_path)

        # Remove store_code from config
        mock_config['test-store'] = {'access_token': 'test-token'}

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            with pytest.raises(Exception, match="store code or access token not found"):
                TestFlippStore(mock_timer_cm)

    def test_flipp_init_missing_access_token_raises_exception(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Flipp initialization raises exception for missing access_token."""
        monkeypatch.chdir(tmp_path)

        # Remove access_token from config
        mock_config['test-store'] = {'store_code': 'TEST123'}

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            with pytest.raises(Exception, match="store code or access token not found"):
                TestFlippStore(mock_timer_cm)


class TestFlippProperties:
    """Test Flipp class properties."""

    def test_store_name_property_getter(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test store_name property getter."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            assert store.store_name == 'test-store'

    def test_store_name_property_setter(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test store_name property setter."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.store_name = 'new-store'
            assert store._store_name == 'new-store'
            assert store.store_name == 'new-store'

    def test_flyer_url_property(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test flyer_url property generates correct URL."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            url = store.flyer_url

            assert 'dam.flippenterprise.net' in url
            assert 'test-store' in url
            assert 'TEST123' in url
            assert 'test-token' in url

    def test_products_url_property(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test products_url property generates correct URL."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.current_flyer_id = 123456

            url = store.products_url

            assert 'dam.flippenterprise.net' in url
            assert '123456' in url
            assert 'test-token' in url

    def test_products_url_property_raises_without_flyer_id(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test products_url property raises exception without flyer_id."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            # Don't set current_flyer_id

            with pytest.raises(Exception, match="Flyer ID not set"):
                _ = store.products_url


class TestFlippGrabFlyers:
    """Test Flipp grab_flyers method."""

    @pytest.mark.asyncio
    async def test_grab_flyers_success(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, mock_flipp_flyers_response):
        """Test successful flyer retrieval."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)

            # Mock httpx client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_flipp_flyers_response)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                async with store:
                    result = await store.grab_flyers()

                assert result == mock_flipp_flyers_response
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_grab_flyers_retry_on_error(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, mock_flipp_flyers_response):
        """Test grab_flyers retries on error."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)

            # First call raises error, second succeeds
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_flipp_flyers_response)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[httpx.ReadTimeout('Timeout'), mock_response]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    async with store:
                        result = await store.grab_flyers()

                    assert result == mock_flipp_flyers_response

    @pytest.mark.asyncio
    async def test_grab_flyers_returns_empty_on_retry_failure(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test grab_flyers returns empty list after retry failure."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)

            # Both calls raise error
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout('Timeout'))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    async with store:
                        result = await store.grab_flyers(is_retry=True)

                    assert result == []


class TestFlippGrabSales:
    """Test Flipp grab_sales method."""

    @pytest.mark.asyncio
    async def test_grab_sales_success(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, mock_flipp_products_response):
        """Test successful sales retrieval."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.current_flyer_id = 123456

            # Mock httpx client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_flipp_products_response)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                async with store:
                    result = []
                    async for item in store.grab_sales():
                        result.append(item)

                    assert len(result) == len(mock_flipp_products_response)

    @pytest.mark.asyncio
    async def test_grab_sales_parses_price_text(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test grab_sales parses price_text correctly."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.current_flyer_id = 123456

            # Mock response with price_text
            mock_products = [
                {
                    'name': 'Product',
                    'brand': 'Brand',
                    'price_text': '$4.99',
                    'pre_price_text': '$5.99',
                    'sale_story': 'Test sale',
                    'valid_from': '2024-01-01T00:00:00',
                    'valid_to': '2024-01-07T23:59:59',
                },
            ]

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_products)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                async with store:
                    result = []
                    async for item in store.grab_sales():
                        result.append(item)

                    # price_text should be converted to float
                    assert result[0]['price_text'] == 4.99

    @pytest.mark.asyncio
    async def test_grab_sales_parses_dates(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test grab_sales parses dates correctly."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.current_flyer_id = 123456

            # Mock response with dates
            mock_products = [
                {
                    'name': 'Product',
                    'brand': 'Brand',
                    'price_text': '4.99',
                    'pre_price_text': '5.99',
                    'sale_story': 'Test sale',
                    'valid_from': '2024-01-01T00:00:00',
                    'valid_to': '2024-01-07T23:59:59',
                },
            ]

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_products)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                async with store:
                    result = []
                    async for item in store.grab_sales():
                        result.append(item)

                    # Dates should be formatted as YYYY-MM-DD
                    assert result[0]['valid_from'] == '2024-01-01'

    @pytest.mark.asyncio
    async def test_grab_sales_handles_invalid_price(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test grab_sales handles invalid price_text."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            store.current_flyer_id = 123456

            # Mock response with invalid price
            mock_products = [
                {
                    'name': 'Product',
                    'brand': 'Brand',
                    'price_text': 'FREE',
                    'pre_price_text': '5.99',
                    'sale_story': 'Test sale',
                    'valid_from': '2024-01-01T00:00:00',
                    'valid_to': '2024-01-07T23:59:59',
                },
            ]

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value=mock_products)
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch('stores.Flipp.Flipp.httpx.AsyncClient', return_value=mock_client):
                async with store:
                    result = []
                    async for item in store.grab_sales():
                        result.append(item)

                    # Should keep original value if conversion fails
                    assert result[0]['price_text'] == 'FREE'


class TestFlippEdgeCases:
    """Test Flipp edge cases."""

    def test_flipp_with_empty_flyer_ids(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Flipp with empty flyer_ids_to_process list."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            assert store.flyer_ids_to_process == []

    def test_flipp_processing_queue_initialized(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Flipp processing_queue is initialized."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestFlippStore(Flipp):
                _store_name = 'test-store'

            store = TestFlippStore(mock_timer_cm)
            assert store.processing_queue == []
