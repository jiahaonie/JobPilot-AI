"""不发起真实网络请求的 DeepSeek 客户端单元测试。"""

import httpx
import pytest
from pydantic import BaseModel

from app.llm.deepseek_client import DeepSeekStructuredClient, _TransientHTTPError
from app.llm.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredOutputError,
)


class ExampleOutput(BaseModel):
    value: int


def _transient(status_code: int) -> _TransientHTTPError:
    """构建与单次请求路径一致的临时错误。"""
    return _TransientHTTPError(status_code, RuntimeError("simulated failure"))


def fake_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def make_client(**overrides) -> DeepSeekStructuredClient:
    return DeepSeekStructuredClient(
        api_key="test-key",
        **overrides,
    )


class TestSuccessAndParsing:
    def test_returns_validated_model_from_response(self, monkeypatch) -> None:
        client = make_client()
        monkeypatch.setattr(
            client,
            "_post_once",
            lambda payload: fake_response('{"value": 42}'),
        )

        result = client.complete_structured(
            prompt="ignored",
            response_model=ExampleOutput,
        )

        assert result.value == 42

    def test_v4_extraction_disables_thinking_and_limits_output(self, monkeypatch) -> None:
        client = make_client(model="deepseek-v4-flash", max_tokens=2048)
        captured = {}

        def fake_post(payload: dict) -> dict:
            captured.update(payload)
            return fake_response('{"value": 42}')

        monkeypatch.setattr(client, "_post_once", fake_post)

        client.complete_structured(prompt="ignored", response_model=ExampleOutput)

        assert captured["thinking"] == {"type": "disabled"}
        assert captured["max_tokens"] == 2048

    def test_raises_structured_error_on_invalid_json(self, monkeypatch) -> None:
        client = make_client()
        monkeypatch.setattr(
            client,
            "_post_once",
            lambda payload: fake_response("not-json"),
        )

        with pytest.raises(StructuredOutputError):
            client.complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )

    def test_raises_structured_error_on_schema_mismatch(self, monkeypatch) -> None:
        client = make_client()
        monkeypatch.setattr(
            client,
            "_post_once",
            lambda payload: fake_response('{"value": "not-an-int"}'),
        )

        with pytest.raises(StructuredOutputError):
            client.complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )

    def test_repairs_one_schema_mismatch_with_explicit_json_schema(
        self,
        monkeypatch,
    ) -> None:
        client = make_client()
        payloads = []

        def fake_post(payload: dict) -> dict:
            payloads.append(payload)
            if len(payloads) == 1:
                return fake_response('{"value": "not-an-int"}')
            return fake_response('{"value": 42}')

        monkeypatch.setattr(client, "_post_once", fake_post)

        result = client.complete_structured(
            prompt="ignored",
            response_model=ExampleOutput,
        )

        assert result.value == 42
        assert len(payloads) == 2
        assert "JSON Schema" in payloads[1]["messages"][-1]["content"]


class TestRetries:
    def test_retries_429_then_fails(self, monkeypatch) -> None:
        client = make_client(max_retries=1)
        calls = {"count": 0}

        def fake_post(_payload: dict) -> dict:
            calls["count"] += 1
            raise _transient(429)

        monkeypatch.setattr(client, "_post_once", fake_post)

        with pytest.raises(LLMRateLimitError):
            client.complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )
        assert calls["count"] == 2  # initial + 1 retry

    def test_succeeds_after_one_retry(self, monkeypatch) -> None:
        client = make_client(max_retries=2)
        calls = {"count": 0}

        def fake_post(_payload: dict) -> dict:
            calls["count"] += 1
            if calls["count"] == 1:
                raise _transient(503)
            return fake_response('{"value": 7}')

        monkeypatch.setattr(client, "_post_once", fake_post)

        result = client.complete_structured(
            prompt="ignored",
            response_model=ExampleOutput,
        )

        assert result.value == 7
        assert calls["count"] == 2

    def test_raises_timeout_after_retries(self, monkeypatch) -> None:
        client = make_client(max_retries=1)

        def raise_timeout(_payload: dict) -> dict:
            raise httpx.ConnectTimeout("connect timeout")

        monkeypatch.setattr(client, "_post_once", raise_timeout)

        with pytest.raises(LLMTimeoutError):
            client.complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )

    def test_real_500_response_retries_then_raises_provider_error(
        self,
        monkeypatch,
    ) -> None:
        """真实响应路径应保留异常对象，而不是绑定方法。"""
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(500, request=request)

        real_client = httpx.Client
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx,
            "Client",
            lambda **kwargs: real_client(transport=transport, **kwargs),
        )

        with pytest.raises(LLMProviderError):
            make_client(max_retries=1).complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )
        assert calls["count"] == 2

    def test_real_400_response_maps_to_provider_error(self, monkeypatch) -> None:
        """不可重试的 HTTP 错误也应转换为统一 LLM 异常。"""
        real_client = httpx.Client
        transport = httpx.MockTransport(lambda request: httpx.Response(400, request=request))
        monkeypatch.setattr(
            httpx,
            "Client",
            lambda **kwargs: real_client(transport=transport, **kwargs),
        )

        with pytest.raises(LLMProviderError):
            make_client().complete_structured(
                prompt="ignored",
                response_model=ExampleOutput,
            )
