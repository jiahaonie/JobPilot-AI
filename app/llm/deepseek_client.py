"""满足结构化输出约定的 DeepSeek 服务商适配器。"""

import json
import logging
from time import perf_counter
from typing import Any

import httpx

from app.llm.client import ModelT
from app.llm.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredOutputError,
)
from app.llm.structured import parse_structured_output

logger = logging.getLogger(__name__)


class _TransientHTTPError(Exception):
    """包装可重试 HTTP 错误，供重试循环识别。"""

    def __init__(self, status_code: int, original: BaseException) -> None:
        super().__init__(status_code)
        self.status_code = status_code
        self.original = original


class DeepSeekStructuredClient:
    """调用 DeepSeek 对话补全接口的 OpenAI 兼容客户端。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        max_tokens: int = 4096,
        thinking_enabled: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.thinking_enabled = thinking_enabled
        self._http_client = httpx.Client(timeout=self.timeout_seconds)

    def complete_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """完成提示词请求并返回指定响应模型的实例。"""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You extract structured information from raw "
                    "text. Return only JSON that matches the requested schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.model.startswith("deepseek-v4"):
            payload["thinking"] = {
                "type": "enabled" if self.thinking_enabled else "disabled"
            }

        started_at = perf_counter()
        response = self._request(payload)
        usage = response.get("usage", {})
        logger.info(
            "LLM structured completion finished model=%s duration_seconds=%.2f "
            "prompt_tokens=%s completion_tokens=%s",
            self.model,
            perf_counter() - started_at,
            usage.get("prompt_tokens", "unknown"),
            usage.get("completion_tokens", "unknown"),
        )
        try:
            return self._parse_content(response, response_model)
        except StructuredOutputError as exc:
            logger.warning(
                "LLM JSON failed schema validation; requesting one corrected response: %s",
                exc,
            )
            try:
                previous_content = self._content(response)
            except (KeyError, IndexError, TypeError):
                raise exc from None
            repair_payload = dict(payload)
            repair_payload["messages"] = [
                *payload["messages"],
                {
                    "role": "assistant",
                    "content": previous_content,
                },
                {
                    "role": "user",
                    "content": (
                        "Correct the previous JSON so it matches this JSON Schema exactly. "
                        "Return JSON only. Schema: "
                        + json.dumps(
                            response_model.model_json_schema(),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                    ),
                },
            ]
            repaired_response = self._request(repair_payload)
            return self._parse_content(repaired_response, response_model)

    def close(self) -> None:
        """释放应用生命周期内复用的 HTTP 连接池。"""
        self._http_client.close()

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """发送对话补全请求，并重试临时错误。"""
        attempt = 0
        while True:
            attempt += 1
            try:
                return self._post_once(payload)
            except httpx.TimeoutException as exc:
                if attempt > self.max_retries:
                    raise LLMTimeoutError("The LLM provider timed out before answering.") from exc
            except httpx.RequestError as exc:
                raise LLMProviderError("The LLM provider request failed.") from exc
            except _TransientHTTPError as exc:
                if attempt > self.max_retries:
                    if exc.status_code == 429:
                        raise LLMRateLimitError(
                            "The LLM provider rate limit was hit and retries were exhausted."
                        ) from exc
                    raise LLMProviderError(
                        f"The LLM provider returned HTTP {exc.status_code}."
                    ) from exc.original
            except httpx.HTTPStatusError as exc:
                raise LLMProviderError(
                    f"The LLM provider returned HTTP {exc.response.status_code}."
                ) from exc

    def _post_once(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行一次网络请求并返回 JSON 响应。"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self._http_client.post(url, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if response.status_code == 429 or response.status_code >= 500:
                raise _TransientHTTPError(response.status_code, exc) from exc
            raise
        try:
            return response.json()
        except ValueError as exc:
            raise StructuredOutputError("The LLM provider response was not valid JSON.") from exc

    def _parse_content(
        self,
        response: dict[str, Any],
        response_model: type[ModelT],
    ) -> ModelT:
        """提取模型载荷，并按响应模型完成校验。"""
        try:
            payload = json.loads(self._content(response))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise StructuredOutputError(
                "The LLM provider response did not contain valid JSON content."
            ) from exc
        return parse_structured_output(payload, response_model)

    @staticmethod
    def _content(response: dict[str, Any]) -> str:
        """提取对话补全正文，供校验与一次修复请求复用。"""
        content = response["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("LLM message content was not a string")
        return content
