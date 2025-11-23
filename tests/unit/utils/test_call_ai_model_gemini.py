"""
Tests for utils/call_ai_model_gemini.py module.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from utils.call_ai_model_gemini import (
    extract_products_using_gemini,
    handle_gemini_response,
    handle_ai_studio_generate,
    handle_vertex_ai_generate,
    make_aistudio_gemini_call,
    make_vertex_gemini_call,
    setup_gemini_prompt,
    tool_def,
)


class TestToolDefinition:
    """Test the tool definition structure."""

    def test_tool_def_has_function_declarations(self):
        """Test that tool_def has function_declarations."""
        assert 'function_declarations' in tool_def
        assert len(tool_def['function_declarations']) > 0

    def test_tool_def_extract_rows_function(self):
        """Test that extract_rows function is defined."""
        func_decl = tool_def['function_declarations'][0]
        assert func_decl['name'] == 'extract_rows'
        assert 'description' in func_decl
        assert 'parameters' in func_decl

    def test_tool_def_has_all_required_fields(self):
        """Test that tool definition has all required product fields."""
        func_decl = tool_def['function_declarations'][0]
        properties = func_decl['parameters']['properties']['products']['items']['properties']

        required_fields = [
            'brand_name',
            'product_name',
            'product_variety',
            'description',
            'required_purchase_quantity',
            'price',
            'sale_percent_off',
            'sale_amount_off',
            'sale_price',
            'quantity_at_sale_price',
            'quantity_get_free',
            'quantity_percent_off',
            'quantity_at_amount_off',
            'deal_type',
            'requires_store_card',
            'valid_from',
            'valid_to',
            'required_purchase_amount',
        ]

        for field in required_fields:
            assert field in properties, f"Missing required field: {field}"

    def test_tool_def_deal_type_enum(self):
        """Test that deal_type has proper enum values."""
        func_decl = tool_def['function_declarations'][0]
        deal_type_prop = func_decl['parameters']['properties']['products']['items']['properties']['deal_type']

        expected_deal_types = [
            'PERCENT_OFF',
            'AMOUNT_OFF',
            'BUY_X_GET_Y_AT_Z_PER_OFF',
            'BUY_X_GET_Y_AT_Z_AMO_OFF',
            'BUY_X_GET_Y_FREE',
            'BUY_X_GET_Y_AMOUNT_OFF',
            'PRICE_PER_AMOUNT',
            'SALE_PRICE',
            'OTHER',
        ]

        assert 'enum' in deal_type_prop
        assert set(deal_type_prop['enum']) == set(expected_deal_types)


class TestHandleGeminiResponse:
    """Test handle_gemini_response function."""

    def test_handle_gemini_response_success(self, mock_gemini_response):
        """Test handling successful Gemini response."""
        items = handle_gemini_response(mock_gemini_response)

        assert isinstance(items, list)
        assert len(items) > 0
        assert 'brand_name' in items[0]
        assert 'product_name' in items[0]

    def test_handle_gemini_response_no_candidates(self):
        """Test handling response with no candidates."""
        mock_response = MagicMock()
        mock_response.candidates = []

        with pytest.raises(KeyError, match="Invalid response"):
            handle_gemini_response(mock_response)

    def test_handle_gemini_response_none(self):
        """Test handling None response."""
        with pytest.raises(KeyError, match="Invalid response"):
            handle_gemini_response(None)

    def test_handle_gemini_response_missing_function_call(self):
        """Test handling response without function_call."""
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()

        # Remove function_call attribute
        del mock_part.function_call

        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        with pytest.raises((KeyError, AttributeError)):
            handle_gemini_response(mock_response)

    def test_handle_gemini_response_no_products(self):
        """Test handling response with no products in arguments."""
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()
        mock_function_call = MagicMock()

        mock_function_call.args = {}  # No products key
        mock_part.function_call = mock_function_call
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        items = handle_gemini_response(mock_response)
        assert items == []

    def test_handle_gemini_response_empty_products(self):
        """Test handling response with empty products list."""
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()
        mock_function_call = MagicMock()

        mock_function_call.args = {'products': []}
        mock_part.function_call = mock_function_call
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        items = handle_gemini_response(mock_response)
        assert items == []


class TestSetupGeminiPrompt:
    """Test setup_gemini_prompt function."""

    @pytest.mark.asyncio
    async def test_setup_gemini_prompt_with_api_key(self, mock_config):
        """Test prompt setup with Google API key."""
        default_section = mock_config['config']
        user_input = {'test': 'data'}

        with patch('utils.call_ai_model_gemini.get_template_with_args', new_callable=AsyncMock) as mock_template:
            mock_template.return_value = "Test prompt template"

            (
                model_name,
                model_temp,
                model_top_k,
                model_top_p,
                prompt_str,
                prompt_input,
            ) = await setup_gemini_prompt(
                default_section=default_section,
                template_arguments={},
                prompt_jinja_template_path='test.jinja',
                user_input_text=user_input,
            )

            assert model_name == 'gemini-1.0-pro-001'
            assert model_temp == 1.0
            assert model_top_k == 40
            assert model_top_p == 0.95
            assert prompt_str == "Test prompt template"
            assert 'test' in prompt_input or 'data' in prompt_input

    @pytest.mark.asyncio
    async def test_setup_gemini_prompt_no_api_key(self):
        """Test prompt setup without Google API key raises exception."""
        default_section = {'OTHER_KEY': 'value'}

        with pytest.raises(Exception, match="No Google API key or project ID"):
            await setup_gemini_prompt(
                default_section=default_section,
                template_arguments={},
                prompt_jinja_template_path='test.jinja',
                user_input_text={'test': 'data'},
            )

    @pytest.mark.asyncio
    async def test_setup_gemini_prompt_string_input(self, mock_config):
        """Test prompt setup with string user input."""
        default_section = mock_config['config']
        user_input = "test string"

        with patch('utils.call_ai_model_gemini.get_template_with_args', new_callable=AsyncMock) as mock_template:
            mock_template.return_value = "Test prompt"

            (
                model_name,
                model_temp,
                model_top_k,
                model_top_p,
                prompt_str,
                prompt_input,
            ) = await setup_gemini_prompt(
                default_section=default_section,
                template_arguments={},
                prompt_jinja_template_path='test.jinja',
                user_input_text=user_input,
            )

            # String input should be wrapped in json code block
            assert 'json' in prompt_input or user_input in prompt_input


class TestMakeVertexGeminiCall:
    """Test make_vertex_gemini_call function."""

    @pytest.mark.asyncio
    async def test_make_vertex_gemini_call_success(self, mock_logger):
        """Test successful Vertex AI Gemini call."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        with patch('utils.call_ai_model_gemini.GenerativeModel', return_value=mock_model):
            history = []
            result = await make_vertex_gemini_call(
                history, mock_logger, model_name='gemini-1.0-pro-001'
            )

            assert result == mock_response
            mock_model.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_vertex_gemini_call_retry_on_429(self, mock_logger):
        """Test retry logic on 429 error."""
        mock_model = MagicMock()
        mock_response = MagicMock()

        # First call raises 429, second succeeds
        mock_model.generate_content_async = AsyncMock(
            side_effect=[Exception('429 Too Many Requests'), mock_response]
        )

        with patch('utils.call_ai_model_gemini.GenerativeModel', return_value=mock_model):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                history = []
                result = await make_vertex_gemini_call(
                    history, mock_logger, model_name='gemini-1.0-pro-001'
                )

                assert result == mock_response
                assert mock_model.generate_content_async.call_count == 2

    @pytest.mark.asyncio
    async def test_make_vertex_gemini_call_max_retries_exceeded(self, mock_logger):
        """Test that exception is raised after max retries."""
        mock_model = MagicMock()

        # Always raise exception
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception('Persistent error')
        )

        with patch('utils.call_ai_model_gemini.GenerativeModel', return_value=mock_model):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                history = []

                with pytest.raises(Exception, match="Persistent error"):
                    await make_vertex_gemini_call(
                        history, mock_logger, model_name='gemini-1.0-pro-001'
                    )

                # Should have tried MAX_RETRIES times
                assert mock_model.generate_content_async.call_count == 3


class TestMakeAIStudioGeminiCall:
    """Test make_aistudio_gemini_call function."""

    @pytest.mark.asyncio
    async def test_make_aistudio_gemini_call_success(self, mock_logger):
        """Test successful AI Studio Gemini call."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        with patch('utils.call_ai_model_gemini.AIStudioGenerativeModel', return_value=mock_model):
            history = []
            result = await make_aistudio_gemini_call(
                history, mock_logger, model_name='gemini-1.0-pro-001'
            )

            assert result == mock_response
            mock_model.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_aistudio_gemini_call_retry_on_429(self, mock_logger):
        """Test retry logic on 429 error."""
        mock_model = MagicMock()
        mock_response = MagicMock()

        # First call raises 429, second succeeds
        mock_model.generate_content_async = AsyncMock(
            side_effect=[Exception('429 Too Many Requests'), mock_response]
        )

        with patch('utils.call_ai_model_gemini.AIStudioGenerativeModel', return_value=mock_model):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                history = []
                result = await make_aistudio_gemini_call(
                    history, mock_logger, model_name='gemini-1.0-pro-001'
                )

                assert result == mock_response
                assert mock_model.generate_content_async.call_count == 2


class TestHandleVertexAIGenerate:
    """Test handle_vertex_ai_generate function."""

    @pytest.mark.asyncio
    async def test_handle_vertex_ai_generate_success(self, mock_logger):
        """Test successful Vertex AI generation."""
        mock_response = MagicMock()

        with patch('utils.call_ai_model_gemini.make_vertex_gemini_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await handle_vertex_ai_generate(
                mock_logger,
                'gemini-1.0-pro-001',
                1.0,
                40,
                0.95,
                'test prompt',
                'test input',
            )

            assert result == mock_response
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_vertex_ai_generate_error(self, mock_logger):
        """Test error handling in Vertex AI generation."""
        with patch('utils.call_ai_model_gemini.make_vertex_gemini_call', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception('Test error')

            result = await handle_vertex_ai_generate(
                mock_logger,
                'gemini-1.0-pro-001',
                1.0,
                40,
                0.95,
                'test prompt',
                'test input',
            )

            assert result is None
            mock_logger.error.assert_called_once()


class TestHandleAIStudioGenerate:
    """Test handle_ai_studio_generate function."""

    @pytest.mark.asyncio
    async def test_handle_ai_studio_generate_success(self, mock_logger):
        """Test successful AI Studio generation."""
        mock_response = MagicMock()

        with patch('utils.call_ai_model_gemini.make_aistudio_gemini_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await handle_ai_studio_generate(
                mock_logger,
                'gemini-1.0-pro-001',
                1.0,
                40,
                0.95,
                'test prompt',
                'test input',
            )

            assert result == mock_response
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ai_studio_generate_error(self, mock_logger):
        """Test error handling in AI Studio generation."""
        with patch('utils.call_ai_model_gemini.make_aistudio_gemini_call', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception('Test error')

            result = await handle_ai_studio_generate(
                mock_logger,
                'gemini-1.0-pro-001',
                1.0,
                40,
                0.95,
                'test prompt',
                'test input',
            )

            assert result is None
            mock_logger.error.assert_called_once()


class TestExtractProductsUsingGemini:
    """Test extract_products_using_gemini function."""

    @pytest.mark.asyncio
    async def test_extract_products_using_gemini_with_api_key(
        self, mock_config, mock_logger, mock_gemini_response
    ):
        """Test product extraction with API key."""
        args = {
            'prompt_jinja_template_path': 'test.jinja',
            'user_input': [{'test': 'data'}],
            'logger': mock_logger,
        }

        with patch('utils.call_ai_model_gemini.get_config', return_value=mock_config):
            with patch('utils.call_ai_model_gemini.get_template_with_args', new_callable=AsyncMock) as mock_template:
                mock_template.return_value = "Test prompt"

                with patch('utils.call_ai_model_gemini.handle_ai_studio_generate', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = mock_gemini_response

                    result = await extract_products_using_gemini(args)

                    assert result is not None
                    products, user_input = result
                    assert isinstance(products, list)
                    assert user_input == [{'test': 'data'}]

    @pytest.mark.asyncio
    async def test_extract_products_using_gemini_no_response(
        self, mock_config, mock_logger
    ):
        """Test product extraction when Gemini returns None."""
        args = {
            'prompt_jinja_template_path': 'test.jinja',
            'user_input': [{'test': 'data'}],
            'logger': mock_logger,
        }

        with patch('utils.call_ai_model_gemini.get_config', return_value=mock_config):
            with patch('utils.call_ai_model_gemini.get_template_with_args', new_callable=AsyncMock) as mock_template:
                mock_template.return_value = "Test prompt"

                with patch('utils.call_ai_model_gemini.handle_ai_studio_generate', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = None

                    result = await extract_products_using_gemini(args)

                    assert result is not None
                    products, user_input = result
                    assert products == []
                    assert user_input == [{'test': 'data'}]

    @pytest.mark.asyncio
    async def test_extract_products_using_gemini_exception(
        self, mock_config, mock_logger, mock_gemini_response
    ):
        """Test product extraction handles exceptions."""
        args = {
            'prompt_jinja_template_path': 'test.jinja',
            'user_input': [{'test': 'data'}],
            'logger': mock_logger,
        }

        with patch('utils.call_ai_model_gemini.get_config', return_value=mock_config):
            with patch('utils.call_ai_model_gemini.get_template_with_args', new_callable=AsyncMock) as mock_template:
                mock_template.return_value = "Test prompt"

                with patch('utils.call_ai_model_gemini.handle_ai_studio_generate', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = mock_gemini_response

                    with patch('utils.call_ai_model_gemini.handle_gemini_response', side_effect=Exception('Test error')):
                        result = await extract_products_using_gemini(args)

                        products, user_input = result
                        assert products == []
                        mock_logger.error.assert_called()
