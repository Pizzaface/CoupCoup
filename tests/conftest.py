"""
Shared test fixtures and configuration for all tests.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import configparser
import tempfile
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pandas as pd
import pytest
from openpyxl import Workbook


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config.ini file for testing."""
    config = configparser.ConfigParser()
    config['config'] = {
        'GOOGLE_API_KEY': 'test-api-key',
        'items_at_once': '5',
        'MODEL_NAME': 'gemini-1.0-pro-001',
        'MODEL_TEMP': '1.0',
        'MODEL_TOP_K': '40',
        'MODEL_TOP_P': '0.95',
        'stores': '["test-store"]',
        'coupon_sources': '["test-coupon"]',
    }
    config['test-store'] = {
        'store_code': 'TEST123',
        'access_token': 'test-token',
    }
    config['directions'] = {
        'api_key': 'test-ors-key',
        'zip_code': '12345',
    }

    config_path = tmp_path / 'config.ini'
    with open(config_path, 'w') as f:
        config.write(f)

    return config_path


@pytest.fixture
def mock_config(temp_config_file):
    """Mock the get_config function to return test config."""
    config = configparser.ConfigParser()
    config.read(temp_config_file)

    with patch('utils.config.get_config', return_value=config):
        yield config


@pytest.fixture
def temp_excel_file(tmp_path):
    """Create a temporary Excel file for testing."""
    excel_path = tmp_path / 'output' / 'stores.xlsx'
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = 'TestStore'
    ws.append(['Brand Name', 'Product Name', 'Price', 'Valid To'])
    wb.save(excel_path)

    return excel_path


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        'brand_name': 'Test Brand',
        'product_name': 'Test Product',
        'product_variety': '12 oz',
        'description': 'Test description',
        'required_purchase_quantity': 1,
        'required_purchase_amount': 0,
        'price': 4.99,
        'sale_percent_off': 0,
        'sale_amount_off': 0,
        'sale_price': 3.99,
        'quantity_at_sale_price': 1,
        'quantity_get_free': 0,
        'quantity_percent_off': 0,
        'quantity_at_amount_off': 0,
        'deal_type': 'SALE_PRICE',
        'requires_store_card': False,
        'valid_from': '2024-01-01',
        'valid_to': '2024-01-07',
    }


@pytest.fixture
def sample_products_list(sample_product_data):
    """Sample list of products for testing."""
    products = []
    for i in range(5):
        product = sample_product_data.copy()
        product['product_name'] = f'Test Product {i}'
        product['price'] = 4.99 + i
        products.append(product)
    return products


@pytest.fixture
def sample_dataframe(sample_products_list):
    """Sample pandas DataFrame for testing."""
    return pd.DataFrame(sample_products_list)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': 'test'}
    mock_response.raise_for_status = Mock()
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response for testing."""
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_content = MagicMock()
    mock_part = MagicMock()
    mock_function_call = MagicMock()

    mock_function_call.args = {
        'products': [
            {
                'brand_name': 'Test Brand',
                'product_name': 'Test Product',
                'product_variety': '12 oz',
                'description': 'Test',
                'required_purchase_quantity': 1,
                'required_purchase_amount': 0,
                'price': 4.99,
                'sale_percent_off': 0,
                'sale_amount_off': 0,
                'sale_price': 3.99,
                'quantity_at_sale_price': 1,
                'quantity_get_free': 0,
                'quantity_percent_off': 0,
                'quantity_at_amount_off': 0,
                'deal_type': 'SALE_PRICE',
                'requires_store_card': False,
                'valid_from': '2024-01-01',
                'valid_to': '2024-01-07',
            }
        ]
    }

    mock_part.function_call = mock_function_call
    mock_content.parts = [mock_part]
    mock_candidate.content = mock_content
    mock_response.candidates = [mock_candidate]

    return mock_response


@pytest.fixture
def mock_timer_cm():
    """Mock timer context manager for testing."""
    mock_timer = MagicMock()
    mock_timer.shift = Mock()
    return mock_timer


@pytest.fixture
def mock_workbook(tmp_path):
    """Create a mock openpyxl Workbook for testing."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'TestSheet'
    ws.append(['Header1', 'Header2', 'Header3'])
    ws.append(['Value1', 'Value2', 'Value3'])

    # Save to temp file
    wb_path = tmp_path / 'test_workbook.xlsx'
    wb.save(wb_path)

    return wb_path


@pytest.fixture
def mock_flipp_flyers_response():
    """Mock Flipp API flyers response."""
    return [
        {
            'id': 123456,
            'name': 'Weekly Ad',
            'valid_from': '2024-01-01T00:00:00',
            'valid_to': '2024-01-07T23:59:59',
            'storefront_ids': [1, 2, 3],
        }
    ]


@pytest.fixture
def mock_flipp_products_response():
    """Mock Flipp API products response."""
    return [
        {
            'name': 'Test Product',
            'brand': 'Test Brand',
            'description': 'Test description',
            'price_text': '$4.99',
            'valid_from': '2024-01-01T00:00:00',
            'valid_to': '2024-01-07T23:59:59',
            'current_price': 4.99,
        }
    ]


@pytest.fixture
def sample_coupon_data():
    """Sample coupon data for testing."""
    return {
        'brand_name': 'Coupon Brand',
        'product_name': 'Coupon Product',
        'product_variety': 'Any variety',
        'description': 'Save $1.00',
        'required_purchase_quantity': 1,
        'required_purchase_amount': 0,
        'price': 0,
        'sale_percent_off': 0,
        'sale_amount_off': 1.00,
        'sale_price': 0,
        'quantity_at_sale_price': 0,
        'quantity_get_free': 0,
        'quantity_percent_off': 0,
        'quantity_at_amount_off': 1,
        'deal_type': 'AMOUNT_OFF',
        'requires_store_card': False,
        'valid_from': '2024-01-01',
        'valid_to': '2024-03-31',
    }


@pytest.fixture
def sample_sales_dataframe():
    """Sample sales DataFrame for matching tests."""
    data = [
        {
            'brand_name': 'Coca-Cola',
            'product_name': 'Coke',
            'product_variety': '12 pk',
            'price': 5.99,
        },
        {
            'brand_name': 'Pepsi',
            'product_name': 'Pepsi Cola',
            'product_variety': '12 pk',
            'price': 5.49,
        },
        {
            'brand_name': 'Kraft',
            'product_name': 'Mac and Cheese',
            'product_variety': '7.25 oz',
            'price': 1.29,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture
def sample_coupons_dataframe():
    """Sample coupons DataFrame for matching tests."""
    data = [
        {
            'brand_name': 'Coca-Cola',
            'product_name': 'Coca Cola Products',
            'product_variety': 'Any variety',
            'sale_amount_off': 1.00,
        },
        {
            'brand_name': 'Kraft',
            'product_name': 'Macaroni & Cheese',
            'product_variety': 'Any variety',
            'sale_amount_off': 0.50,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture
def mock_logger():
    """Mock loguru logger for testing."""
    mock_log = MagicMock()
    mock_log.info = Mock()
    mock_log.warning = Mock()
    mock_log.error = Mock()
    mock_log.debug = Mock()
    mock_log.patch = Mock(return_value=mock_log)
    return mock_log


@pytest.fixture
async def mock_pyppeteer_browser():
    """Mock Pyppeteer browser for testing."""
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.waitForSelector = AsyncMock()
    mock_page.querySelectorAll = AsyncMock(return_value=[])
    mock_page.close = AsyncMock()
    mock_browser.newPage = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    return mock_browser


@pytest.fixture
def httpx_mock_transport():
    """Create a mock HTTPX transport for testing."""
    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.responses = []
            self.call_count = 0

        async def handle_async_request(self, request):
            self.call_count += 1
            if self.responses:
                return self.responses.pop(0)

            # Default response
            return httpx.Response(
                200,
                json={'data': 'test'},
                request=request,
            )

    return MockTransport()


@pytest.fixture
def cleanup_excel_files():
    """Cleanup any Excel files created during tests."""
    yield
    # Cleanup after test
    output_dir = Path('output')
    if output_dir.exists():
        for file in output_dir.glob('*.xlsx'):
            try:
                file.unlink()
            except:
                pass
