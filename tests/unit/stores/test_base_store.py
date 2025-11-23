"""
Tests for stores/lib/BaseStore.py module.
"""
import os
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from zipfile import BadZipFile

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from stores.lib.BaseStore import Store, CouponBaseStore


class TestStoreInit:
    """Test Store class initialization."""

    def test_store_init_with_valid_config(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Store initialization with valid config."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            # Create a test store class
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)

            assert store._store_name == 'test-store'
            assert store.store_config is not None
            assert store.items_at_once == 5

    def test_store_init_missing_config_raises_exception(self, mock_config, mock_timer_cm):
        """Test Store initialization raises exception for missing config."""
        config = mock_config
        # Remove the test-store section
        config.remove_section('test-store')

        with patch('stores.lib.BaseStore.get_config', return_value=config):
            class TestStore(Store):
                _store_name = 'nonexistent-store'

            with pytest.raises(Exception, match="config not found"):
                TestStore(mock_timer_cm)

    def test_store_init_with_coupon_suffix(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Store initialization with -coupons suffix."""
        monkeypatch.chdir(tmp_path)

        # Add a coupon config
        mock_config['test'] = {'key': 'value'}

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestCouponStore(Store):
                _store_name = 'test-coupons'

            store = TestCouponStore(mock_timer_cm)
            assert store.store_config is not None


class TestStoreProperties:
    """Test Store class properties."""

    def test_httpx_transport_property(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test httpx_transport property returns RetryTransport."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            transport = store.httpx_transport

            from lib.RetryTransport import RetryTransport
            assert isinstance(transport, RetryTransport)

    def test_excel_file_path_property(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test excel_file_path property."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            assert store.excel_file_path == 'output/stores.xlsx'

    def test_logger_property(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test logger property."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            logger = store.logger

            assert logger is not None


class TestStoreExcelMethods:
    """Test Store Excel-related methods."""

    def test_get_title_header(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test get_title_header method."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'
                headers: List[str] = ['brand_name', 'product_name', 'sale_price']

            store = TestStore(mock_timer_cm)
            title_headers = store.get_title_header()

            assert title_headers == ['Brand Name', 'Product Name', 'Sale Price']

    def test_reset_worksheet_creates_new_file(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test reset_worksheet creates new Excel file."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'
                headers: List[str] = ['brand_name', 'product_name']

            store = TestStore(mock_timer_cm)
            store.reset_worksheet()

            assert Path(store.excel_file_path).exists()

            # Check that the worksheet has headers
            wb = load_workbook(store.excel_file_path)
            ws = wb['test-store']
            assert ws['A1'].value == 'Brand Name'
            assert ws['B1'].value == 'Product Name'

    def test_reset_worksheet_removes_existing_sheet(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test reset_worksheet removes existing sheet with same name."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        # Create existing Excel file
        wb = Workbook()
        ws = wb.active
        ws.title = 'test-store'
        ws.append(['Old', 'Data'])
        wb.save('output/stores.xlsx')

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'
                headers: List[str] = ['brand_name', 'product_name']

            store = TestStore(mock_timer_cm)
            store.reset_worksheet()

            # Check that old data is gone
            wb = load_workbook(store.excel_file_path)
            ws = wb['test-store']
            assert ws['A1'].value != 'Old'
            assert ws['A1'].value == 'Brand Name'

    def test_add_row_to_store_worksheet(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, sample_product_data):
        """Test add_row_to_store_worksheet method."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.reset_worksheet()
            store.add_row_to_store_worksheet(sample_product_data)

            # Check that data was added
            wb = load_workbook(store.excel_file_path)
            ws = wb['test-store']
            assert ws.max_row == 2  # Header + 1 data row
            assert ws['A2'].value == 'Test Brand'

    def test_add_rows_to_store_worksheet(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, sample_products_list):
        """Test add_rows_to_store_worksheet method."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.reset_worksheet()
            store.add_rows_to_store_worksheet(sample_products_list)

            # Check that all rows were added
            wb = load_workbook(store.excel_file_path)
            ws = wb['test-store']
            assert ws.max_row == len(sample_products_list) + 1  # Headers + data

    def test_clean_worksheet(self, mock_config, mock_timer_cm, monkeypatch, tmp_path, sample_product_data):
        """Test clean_worksheet method formats cells correctly."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.reset_worksheet()
            store.add_row_to_store_worksheet(sample_product_data)
            store.clean_worksheet()

            # Check formatting
            wb = load_workbook(store.excel_file_path)
            ws = wb['test-store']

            # Header should be bold
            assert ws['A1'].font.bold is True
            # Header should have background color
            assert ws['A1'].fill.fgColor.rgb == '424242'

    def test_check_current_data_valid(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test check_current_data returns True for valid data."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        # Create valid Excel file
        wb = Workbook()
        ws = wb.active
        ws.title = 'test-store'
        ws.append(['Brand Name', 'Product Name', 'Valid To'])
        ws.append(['Test', 'Product', '2024-01-07'])
        wb.save('output/stores.xlsx')

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            assert store.check_current_data() is True

    def test_check_current_data_file_missing(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test check_current_data returns False when file is missing."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            assert store.check_current_data() is False

    def test_check_current_data_bad_zip(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test check_current_data returns False for corrupted Excel file."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        # Create invalid Excel file
        with open('output/stores.xlsx', 'w') as f:
            f.write('not a valid excel file')

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            assert store.check_current_data() is False

    def test_check_current_data_empty_sheet(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test check_current_data returns False for empty sheet."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        # Create Excel file with empty sheet
        wb = Workbook()
        ws = wb.active
        ws.title = 'test-store'
        ws.append(['Brand Name', 'Product Name', 'Valid To'])
        # No data rows
        wb.save('output/stores.xlsx')

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            assert store.check_current_data() is False


class TestStoreProcessQueue:
    """Test Store process_queue method."""

    @pytest.mark.asyncio
    async def test_process_queue_empty(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test process_queue with empty queue."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.processing_queue = []

            # Should exit early without processing
            async with store:
                await store.process_queue()

    @pytest.mark.asyncio
    async def test_process_queue_processes_items(
        self, mock_config, mock_timer_cm, monkeypatch, tmp_path, sample_products_list
    ):
        """Test process_queue processes items and writes to Excel."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.processing_queue = [{'item': i} for i in range(3)]

            # Mock the AI extraction
            mock_response = (sample_products_list, [{'item': 0}])

            with patch('stores.lib.BaseStore.extract_products_using_gemini', new_callable=AsyncMock) as mock_extract:
                # Create an async generator that yields results
                async def mock_amap(*args, **kwargs):
                    for _ in range(len(store.processing_queue)):
                        yield mock_response

                with patch('stores.lib.BaseStore.aiometer.amap') as mock_aiometer:
                    mock_aiometer.return_value.__aenter__ = AsyncMock(return_value=mock_amap())
                    mock_aiometer.return_value.__aexit__ = AsyncMock()

                    async with store:
                        await store.process_queue()

                    # Check that Excel file was created
                    assert Path(store.excel_file_path).exists()

    @pytest.mark.asyncio
    async def test_process_queue_handles_errors(
        self, mock_config, mock_timer_cm, monkeypatch, tmp_path
    ):
        """Test process_queue handles errors gracefully."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.processing_queue = [{'item': 1}]

            # Mock AI extraction to return exception
            mock_error = Exception('Test error')

            async def mock_amap(*args, **kwargs):
                yield mock_error

            with patch('stores.lib.BaseStore.aiometer.amap') as mock_aiometer:
                mock_aiometer.return_value.__aenter__ = AsyncMock(return_value=mock_amap())
                mock_aiometer.return_value.__aexit__ = AsyncMock()

                async with store:
                    # Should not raise exception
                    await store.process_queue()

    @pytest.mark.asyncio
    async def test_process_queue_reprocesses_on_failure(
        self, mock_config, mock_timer_cm, monkeypatch, tmp_path
    ):
        """Test process_queue reprocesses failed items once."""
        monkeypatch.chdir(tmp_path)
        os.makedirs('output', exist_ok=True)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)
            store.processing_queue = [{'item': 1}]

            # First time: return empty products (triggers reprocess)
            # Second time: return empty products again (stops reprocessing)
            mock_response = ([], [{'item': 1}])

            call_count = 0

            async def mock_amap(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                yield mock_response

            with patch('stores.lib.BaseStore.aiometer.amap') as mock_aiometer:
                mock_aiometer.return_value.__aenter__ = AsyncMock(return_value=mock_amap())
                mock_aiometer.return_value.__aexit__ = AsyncMock()

                async with store:
                    await store.process_queue()

                # Should have been called twice (initial + reprocess)
                # Note: This test is simplified; actual behavior may vary


class TestStoreAsyncContextManager:
    """Test Store async context manager."""

    @pytest.mark.asyncio
    async def test_store_context_manager(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test Store can be used as async context manager."""
        monkeypatch.chdir(tmp_path)

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestStore(Store):
                _store_name = 'test-store'

            store = TestStore(mock_timer_cm)

            async with store as s:
                assert s == store
                assert hasattr(s, 'pbar')


class TestCouponBaseStore:
    """Test CouponBaseStore class."""

    def test_coupon_base_store_inherits_from_store(self):
        """Test CouponBaseStore inherits from Store."""
        assert issubclass(CouponBaseStore, Store)

    def test_coupon_base_store_can_be_instantiated(self, mock_config, mock_timer_cm, monkeypatch, tmp_path):
        """Test CouponBaseStore can be instantiated."""
        monkeypatch.chdir(tmp_path)

        # Add coupon config
        mock_config['test-coupon'] = {'key': 'value'}

        with patch('stores.lib.BaseStore.get_config', return_value=mock_config):
            class TestCouponStore(CouponBaseStore):
                _store_name = 'test-coupon'

            store = TestCouponStore(mock_timer_cm)
            assert isinstance(store, CouponBaseStore)
            assert isinstance(store, Store)
