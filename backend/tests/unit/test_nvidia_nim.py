"""Unit tests for NimClient retry logic (httpx mocked)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.errors import APIError, ErrorCode
from app.services.nvidia_nim import NimClient
from app.services.nvidia_nim_mock import MockNimClient


def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.raise_for_status = MagicMock()
    return resp


_SUCCESS_BODY = {
    "choices": [{"message": {"content": '{"result": "ok"}'}}]
}

_CLIENT_KWARGS = dict(
    model="test-model",
    system="jd_analyzer You analyze job descriptions.",
    user="Analyze this JD.",
)


class TestNimClientSuccess:
    async def test_returns_content_on_200(self):
        resp = _make_response(200, _SUCCESS_BODY)
        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_http

            client = NimClient(api_key="nvapi-test", base_url="https://nim.example.com/v1")
            result = await client.complete(**_CLIENT_KWARGS)

        assert result == '{"result": "ok"}'


class TestNimClientErrors:
    async def test_401_raises_nim_key_invalid(self):
        resp = _make_response(401)
        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_http

            client = NimClient(api_key="bad-key", base_url="https://nim.example.com/v1")
            with pytest.raises(APIError) as exc_info:
                await client.complete(**_CLIENT_KWARGS)

        assert exc_info.value.code == ErrorCode.NIM_KEY_INVALID
        assert exc_info.value.retry_possible is False

    async def test_429_after_max_retries_raises_rate_limited(self):
        resp = _make_response(429)
        with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep") as mock_sleep:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_http

            client = NimClient(api_key="nvapi-test", base_url="https://nim.example.com/v1")
            with pytest.raises(APIError) as exc_info:
                await client.complete(**_CLIENT_KWARGS)

        assert exc_info.value.code == ErrorCode.NIM_RATE_LIMITED
        assert mock_sleep.await_count == 3  # 3 waits before final failure

    async def test_5xx_after_max_retries_raises_model_unavailable(self):
        resp = _make_response(503)
        with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep") as mock_sleep:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=resp)
            mock_cls.return_value = mock_http

            client = NimClient(api_key="nvapi-test", base_url="https://nim.example.com/v1")
            with pytest.raises(APIError) as exc_info:
                await client.complete(**_CLIENT_KWARGS)

        assert exc_info.value.code == ErrorCode.NIM_MODEL_UNAVAILABLE
        assert mock_sleep.await_count == 3

    async def test_timeout_raises_model_unavailable(self):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
            mock_cls.return_value = mock_http

            client = NimClient(api_key="nvapi-test", base_url="https://nim.example.com/v1")
            with pytest.raises(APIError) as exc_info:
                await client.complete(**_CLIENT_KWARGS)

        assert exc_info.value.code == ErrorCode.NIM_MODEL_UNAVAILABLE

    async def test_succeeds_on_second_attempt_after_5xx(self):
        fail_resp = _make_response(503)
        ok_resp = _make_response(200, _SUCCESS_BODY)
        with patch("httpx.AsyncClient") as mock_cls, patch("asyncio.sleep"):
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=[fail_resp, ok_resp])
            mock_cls.return_value = mock_http

            client = NimClient(api_key="nvapi-test", base_url="https://nim.example.com/v1")
            result = await client.complete(**_CLIENT_KWARGS)

        assert result == '{"result": "ok"}'


class TestMockNimClient:
    async def test_returns_jd_analyzer_response(self):
        client = MockNimClient()
        result = await client.complete(
            model="test",
            system="jd_analyzer You analyze JDs.",
            user="Analyze this.",
        )
        data = json.loads(result)
        assert "keywords" in data

    async def test_returns_tailor_response(self):
        client = MockNimClient()
        result = await client.complete(
            model="test",
            system="tailor You select bullets.",
            user="Select bullets.",
        )
        data = json.loads(result)
        assert "experience" in data and "projects" in data

    async def test_unknown_key_returns_default(self):
        client = MockNimClient()
        result = await client.complete(
            model="test", system="unknown_agent does stuff", user="do stuff"
        )
        data = json.loads(result)
        assert "result" in data
