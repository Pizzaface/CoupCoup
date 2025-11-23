"""
Tests for lib/RetryTransport.py module.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from lib.RetryTransport import RetryTransport


class TestRetryTransportInit:
    """Test cases for RetryTransport initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped)

        assert transport._max_attempts == 10
        assert transport._backoff_factor == 0.1
        assert transport._max_backoff_wait == 60
        assert transport._jitter_ratio == 0.1
        assert transport._respect_retry_after_header is True

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(
            wrapped,
            max_attempts=5,
            max_backoff_wait=30,
            backoff_factor=0.2,
            jitter_ratio=0.2,
            respect_retry_after_header=False,
        )

        assert transport._max_attempts == 5
        assert transport._backoff_factor == 0.2
        assert transport._max_backoff_wait == 30
        assert transport._jitter_ratio == 0.2
        assert transport._respect_retry_after_header is False

    def test_init_with_invalid_jitter_ratio(self):
        """Test initialization with invalid jitter ratio raises ValueError."""
        wrapped = httpx.AsyncHTTPTransport()

        with pytest.raises(ValueError, match="between 0 and 0.5"):
            RetryTransport(wrapped, jitter_ratio=-0.1)

        with pytest.raises(ValueError, match="between 0 and 0.5"):
            RetryTransport(wrapped, jitter_ratio=0.6)

    def test_init_with_custom_retryable_methods(self):
        """Test initialization with custom retryable methods."""
        wrapped = httpx.AsyncHTTPTransport()
        custom_methods = ['GET', 'POST']
        transport = RetryTransport(wrapped, retryable_methods=custom_methods)

        assert transport._retryable_methods == frozenset(custom_methods)

    def test_init_with_custom_retry_status_codes(self):
        """Test initialization with custom retry status codes."""
        wrapped = httpx.AsyncHTTPTransport()
        custom_codes = [429, 500]
        transport = RetryTransport(wrapped, retry_status_codes=custom_codes)

        assert transport._retry_status_codes == frozenset(custom_codes)


class TestRetryTransportCalculateSleep:
    """Test cases for _calculate_sleep method."""

    def test_calculate_sleep_basic_backoff(self):
        """Test basic exponential backoff calculation."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, backoff_factor=0.1, jitter_ratio=0)

        # First retry: 0.1 * (2^0) = 0.1
        sleep1 = transport._calculate_sleep(1, {})
        assert 0.05 <= sleep1 <= 0.15

        # Second retry: 0.1 * (2^1) = 0.2
        sleep2 = transport._calculate_sleep(2, {})
        assert 0.15 <= sleep2 <= 0.25

    def test_calculate_sleep_with_jitter(self):
        """Test backoff calculation with jitter."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, backoff_factor=1.0, jitter_ratio=0.1)

        sleep_time = transport._calculate_sleep(1, {})
        # With jitter, should vary slightly from 1.0
        assert 0.8 <= sleep_time <= 1.2

    def test_calculate_sleep_respects_max_backoff(self):
        """Test that sleep time respects max_backoff_wait."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(
            wrapped, backoff_factor=10.0, max_backoff_wait=5.0, jitter_ratio=0
        )

        # Even with high attempts, should not exceed max
        sleep_time = transport._calculate_sleep(10, {})
        assert sleep_time <= 5.0

    def test_calculate_sleep_with_retry_after_header_numeric(self):
        """Test sleep calculation with numeric Retry-After header."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, respect_retry_after_header=True)

        headers = {'Retry-After': '30'}
        sleep_time = transport._calculate_sleep(1, headers)
        assert sleep_time == 30.0

    def test_calculate_sleep_with_retry_after_header_date(self):
        """Test sleep calculation with date Retry-After header."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, respect_retry_after_header=True)

        # Create a future date
        future = datetime.now() + timedelta(seconds=45)
        future_str = future.isoformat()

        headers = {'Retry-After': future_str}
        sleep_time = transport._calculate_sleep(1, headers)

        # Should be close to 45 seconds (with some tolerance for execution time)
        assert 40 <= sleep_time <= 50

    def test_calculate_sleep_ignores_retry_after_when_disabled(self):
        """Test that Retry-After is ignored when respect_retry_after_header is False."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(
            wrapped, respect_retry_after_header=False, backoff_factor=0.1, jitter_ratio=0
        )

        headers = {'Retry-After': '100'}
        sleep_time = transport._calculate_sleep(1, headers)

        # Should use backoff calculation, not the header value
        assert sleep_time < 10

    def test_calculate_sleep_with_malformed_retry_after(self):
        """Test sleep calculation with malformed Retry-After header."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(
            wrapped, respect_retry_after_header=True, backoff_factor=0.1, jitter_ratio=0
        )

        headers = {'Retry-After': 'invalid'}
        sleep_time = transport._calculate_sleep(1, headers)

        # Should fall back to backoff calculation
        assert 0.05 <= sleep_time <= 0.15

    def test_calculate_sleep_retry_after_exceeds_max(self):
        """Test that Retry-After is capped at max_backoff_wait."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(
            wrapped, respect_retry_after_header=True, max_backoff_wait=30.0
        )

        headers = {'Retry-After': '100'}
        sleep_time = transport._calculate_sleep(1, headers)

        # Should be capped at max_backoff_wait
        assert sleep_time <= 30.0


class TestRetryTransportAsyncRequest:
    """Test cases for async request handling."""

    @pytest.mark.asyncio
    async def test_handle_async_request_success_first_try(self):
        """Test successful request on first attempt."""
        # Create mock transport
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_response = httpx.Response(200, json={'success': True})
        mock_transport.handle_async_request = AsyncMock(return_value=mock_response)

        retry_transport = RetryTransport(mock_transport)
        request = httpx.Request('GET', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_async_request.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_async_request_retries_on_429(self):
        """Test that requests are retried on 429 status."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)

        # First two calls return 429, third returns 200
        responses = [
            httpx.Response(429, request=httpx.Request('GET', 'https://example.com')),
            httpx.Response(429, request=httpx.Request('GET', 'https://example.com')),
            httpx.Response(200, json={'success': True}, request=httpx.Request('GET', 'https://example.com')),
        ]
        mock_transport.handle_async_request = AsyncMock(side_effect=responses)

        retry_transport = RetryTransport(mock_transport, backoff_factor=0.01)
        request = httpx.Request('GET', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_async_request.call_count == 3

    @pytest.mark.asyncio
    async def test_handle_async_request_max_attempts_exceeded(self):
        """Test that retries stop after max_attempts."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)

        # Always return 429
        mock_response = httpx.Response(429, request=httpx.Request('GET', 'https://example.com'))
        mock_transport.handle_async_request = AsyncMock(return_value=mock_response)

        retry_transport = RetryTransport(
            mock_transport, max_attempts=3, backoff_factor=0.01
        )
        request = httpx.Request('GET', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        # Should return the 429 after exhausting retries
        assert response.status_code == 429
        # Should try max_attempts times
        assert mock_transport.handle_async_request.call_count == 3

    @pytest.mark.asyncio
    async def test_handle_async_request_non_retryable_method(self):
        """Test that non-retryable methods are not retried."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_response = httpx.Response(429, request=httpx.Request('POST', 'https://example.com'))
        mock_transport.handle_async_request = AsyncMock(return_value=mock_response)

        # POST is not in default retryable methods
        retry_transport = RetryTransport(mock_transport)
        request = httpx.Request('POST', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        # Should not retry
        assert response.status_code == 429
        assert mock_transport.handle_async_request.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_async_request_retries_configurable_status_codes(self):
        """Test retrying custom status codes."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)

        responses = [
            httpx.Response(503, request=httpx.Request('GET', 'https://example.com')),
            httpx.Response(200, json={'success': True}, request=httpx.Request('GET', 'https://example.com')),
        ]
        mock_transport.handle_async_request = AsyncMock(side_effect=responses)

        retry_transport = RetryTransport(
            mock_transport, retry_status_codes=[503], backoff_factor=0.01
        )
        request = httpx.Request('GET', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_async_request.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_async_request_does_not_retry_200(self):
        """Test that successful responses are not retried."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_response = httpx.Response(200, json={'success': True})
        mock_transport.handle_async_request = AsyncMock(return_value=mock_response)

        retry_transport = RetryTransport(mock_transport)
        request = httpx.Request('GET', 'https://example.com')

        response = await retry_transport.handle_async_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_async_request.call_count == 1

    @pytest.mark.asyncio
    async def test_aclose(self):
        """Test aclose method calls wrapped transport's aclose."""
        mock_transport = AsyncMock(spec=httpx.AsyncBaseTransport)
        mock_transport.aclose = AsyncMock()

        retry_transport = RetryTransport(mock_transport)
        await retry_transport.aclose()

        mock_transport.aclose.assert_called_once()


class TestRetryTransportSyncRequest:
    """Test cases for sync request handling."""

    def test_handle_request_success_first_try(self):
        """Test successful sync request on first attempt."""
        mock_transport = Mock(spec=httpx.BaseTransport)
        mock_response = httpx.Response(200, json={'success': True})
        mock_transport.handle_request = Mock(return_value=mock_response)

        retry_transport = RetryTransport(mock_transport)
        request = httpx.Request('GET', 'https://example.com')

        response = retry_transport.handle_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_request.call_count == 1

    def test_handle_request_retries_on_429(self):
        """Test that sync requests are retried on 429 status."""
        mock_transport = Mock(spec=httpx.BaseTransport)

        # First call returns 429, second returns 200
        responses = [
            httpx.Response(429, request=httpx.Request('GET', 'https://example.com')),
            httpx.Response(200, json={'success': True}, request=httpx.Request('GET', 'https://example.com')),
        ]
        mock_transport.handle_request = Mock(side_effect=responses)

        retry_transport = RetryTransport(mock_transport, backoff_factor=0.01)
        request = httpx.Request('GET', 'https://example.com')

        response = retry_transport.handle_request(request)

        assert response.status_code == 200
        assert mock_transport.handle_request.call_count == 2

    def test_close(self):
        """Test close method calls wrapped transport's close."""
        mock_transport = Mock(spec=httpx.BaseTransport)
        mock_transport.close = Mock()

        retry_transport = RetryTransport(mock_transport)
        retry_transport.close()

        mock_transport.close.assert_called_once()


class TestRetryTransportEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_max_attempts(self):
        """Test with zero max attempts."""
        mock_transport = Mock(spec=httpx.BaseTransport)
        mock_response = httpx.Response(429, request=httpx.Request('GET', 'https://example.com'))
        mock_transport.handle_request = Mock(return_value=mock_response)

        retry_transport = RetryTransport(mock_transport, max_attempts=0)
        request = httpx.Request('GET', 'https://example.com')

        response = retry_transport.handle_request(request)

        # Should not retry at all
        assert response.status_code == 429

    def test_jitter_ratio_zero(self):
        """Test with zero jitter ratio."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, jitter_ratio=0, backoff_factor=1.0)

        sleep_time = transport._calculate_sleep(1, {})
        # Without jitter, should be exactly 1.0
        assert sleep_time == 1.0

    def test_jitter_ratio_max(self):
        """Test with maximum jitter ratio."""
        wrapped = httpx.AsyncHTTPTransport()
        transport = RetryTransport(wrapped, jitter_ratio=0.5, backoff_factor=1.0)

        sleep_time = transport._calculate_sleep(1, {})
        # With 0.5 jitter on 1.0 backoff, should be between 0.5 and 1.5
        assert 0.5 <= sleep_time <= 1.5

    @pytest.mark.parametrize(
        "status_code,should_retry",
        [
            (200, False),
            (201, False),
            (400, False),
            (401, False),
            (404, False),
            (429, True),
            (500, True),
            (502, True),
            (503, True),
            (504, True),
        ],
    )
    def test_retry_status_codes(self, status_code, should_retry):
        """Parametrized test for different status codes."""
        mock_transport = Mock(spec=httpx.BaseTransport)

        if should_retry:
            # If should retry, first return error, then success
            responses = [
                httpx.Response(status_code, request=httpx.Request('GET', 'https://example.com')),
                httpx.Response(200, json={'success': True}, request=httpx.Request('GET', 'https://example.com')),
            ]
            mock_transport.handle_request = Mock(side_effect=responses)
        else:
            # If should not retry, just return the status
            mock_transport.handle_request = Mock(
                return_value=httpx.Response(status_code, request=httpx.Request('GET', 'https://example.com'))
            )

        retry_transport = RetryTransport(mock_transport, backoff_factor=0.01)
        request = httpx.Request('GET', 'https://example.com')

        response = retry_transport.handle_request(request)

        if should_retry:
            # Should have retried and gotten 200
            assert response.status_code == 200
            assert mock_transport.handle_request.call_count == 2
        else:
            # Should not have retried
            assert response.status_code == status_code
            assert mock_transport.handle_request.call_count == 1
