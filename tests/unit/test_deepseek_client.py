"""Unit tests for the DeepSeek client without a real network call."""

import httpx
import pytest
from pydantic import BaseModel

from app.llm.deepseek_client import DeepSeekStructuredClient, _TransientHTTPError
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredOutputError,
)


class ExampleOutput(BaseModel):
    value: int


def _transient(status_code: int) -> _TransientHTTPError:
    """Build a transient error like _post_once would raise."""

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
