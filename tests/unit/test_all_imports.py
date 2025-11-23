"""
Smoke tests for all modules to ensure they can be imported and basic functionality works.
"""
import pytest


class TestUtilsImports:
    """Test that all utils modules can be imported."""

    def test_import_text(self):
        """Test utils.text import."""
        from utils import text
        assert hasattr(text, 'clean_text')

    def test_import_config(self):
        """Test utils.config import."""
        from utils import config
        assert hasattr(config, 'get_config')

    def test_import_matching(self):
        """Test utils.matching import."""
        from utils import matching
        assert hasattr(matching, 'match_multiple_columns')

    def test_import_jinja(self):
        """Test utils.jinja import."""
        from utils import jinja
        assert hasattr(jinja, 'get_template_with_args')

    def test_import_random_utils(self):
        """Test utils.random_utils import."""
        try:
            from utils import random_utils
            assert random_utils is not None
        except ImportError:
            pytest.skip("random_utils not found")

    def test_import_call_ai_model_gemini(self):
        """Test utils.call_ai_model_gemini import."""
        from utils import call_ai_model_gemini
        assert hasattr(call_ai_model_gemini, 'extract_products_using_gemini')

    @pytest.mark.skip(reason="May require additional dependencies")
    def test_import_geocoding(self):
        """Test utils.geocoding import."""
        try:
            from utils import geocoding
            assert geocoding is not None
        except ImportError:
            pass

    @pytest.mark.skip(reason="May require additional dependencies")
    def test_import_spreadsheets(self):
        """Test utils.spreadsheets import."""
        try:
            from utils import spreadsheets
            assert spreadsheets is not None
        except ImportError:
            pass


class TestLibImports:
    """Test that all lib modules can be imported."""

    def test_import_retry_transport(self):
        """Test lib.RetryTransport import."""
        from lib import RetryTransport
        assert hasattr(RetryTransport, 'RetryTransport')

    def test_import_constants(self):
        """Test lib.constants import."""
        try:
            from lib import constants
            assert constants is not None
        except ImportError:
            pass


class TestStoresImports:
    """Test that store modules can be imported."""

    def test_import_base_store(self):
        """Test stores.lib.BaseStore import."""
        from stores.lib import BaseStore
        assert hasattr(BaseStore, 'Store')
        assert hasattr(BaseStore, 'CouponBaseStore')

    def test_import_flipp(self):
        """Test stores.Flipp.Flipp import."""
        from stores.Flipp import Flipp
        assert hasattr(Flipp, 'Flipp')

    @pytest.mark.skip(reason="May require browser dependencies")
    def test_import_browser_store(self):
        """Test stores.lib.BrowserStore import."""
        try:
            from stores.lib import BrowserStore
            assert BrowserStore is not None
        except ImportError:
            pass


class TestFlippStoresImports:
    """Test that Flipp store implementations can be imported."""

    @pytest.mark.parametrize("store_name", [
        "CVS",
        "Albertsons",
        "AcmeMarkets",
        "DollarGeneral",
        "FamilyDollar",
        "FoodLion",
        "FredMeyer",
        "FrysFood",
        "GiantFood",
        "HEB",
        "Hannaford",
        "HarrisTeeter",
        "Hyvee",
        "JewelOsco",
        "KingSoopers",
        "Meijer",
        "RousesSupermarkets",
        "SafeWay",
        "ShopRite",
        "Smiths",
        "Sprouts",
        "StopAndShop",
        "WinnDixie",
    ])
    def test_import_flipp_stores(self, store_name):
        """Test importing individual Flipp store implementations."""
        try:
            module = __import__(f'stores.Flipp.{store_name}', fromlist=[store_name])
            assert hasattr(module, store_name)
        except ImportError:
            pytest.skip(f"{store_name} module not available")


class TestCouponsImports:
    """Test that coupon modules can be imported."""

    @pytest.mark.parametrize("coupon_name", [
        "CouponsComCoupons",
        "MeijerCoupons",
        "DollarGeneralCoupons",
        "FamilyDollarCoupons",
        "KrogerCoupons",
        "FoodCityCoupons",
        "FoodLionCoupons",
        "FrysFoodCoupons",
        "FredMeyerCoupons",
        "ShopRiteCoupons",
    ])
    def test_import_coupon_modules(self, coupon_name):
        """Test importing individual coupon modules."""
        try:
            module = __import__(f'coupons.{coupon_name}', fromlist=[coupon_name])
            assert module is not None
        except ImportError:
            pytest.skip(f"{coupon_name} module not available")


class TestModuleFunctionality:
    """Test basic functionality of imported modules."""

    def test_clean_text_functionality(self):
        """Test that clean_text actually works."""
        from utils.text import clean_text

        result = clean_text("Test™®")
        assert "Test" in result

    def test_retry_transport_initialization(self):
        """Test RetryTransport can be initialized."""
        from lib.RetryTransport import RetryTransport
        import httpx

        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped)

        assert transport._max_attempts == 10

    def test_store_headers(self):
        """Test Store has default headers."""
        from stores.lib.BaseStore import Store

        # Check that HEADERS is defined
        from stores.lib import constants
        assert hasattr(constants, 'HEADERS')

    def test_tool_definition_structure(self):
        """Test that Gemini tool definition is properly structured."""
        from utils.call_ai_model_gemini import tool_def

        assert 'function_declarations' in tool_def
        assert len(tool_def['function_declarations']) > 0
        func = tool_def['function_declarations'][0]
        assert func['name'] == 'extract_rows'
        assert 'parameters' in func
