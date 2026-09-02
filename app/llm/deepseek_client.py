"""满足结构化输出约定的 DeepSeek 服务商适配器。"""

import json
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
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

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
            "response_format": {"type": "json_object"},
        }

        response = self._request(payload)
        return self._parse_content(response, response_model)

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
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
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
            content = response["choices"][0]["message"]["content"]
            payload = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise StructuredOutputError(
                "The LLM provider response did not contain valid JSON content."
            ) from exc
        return parse_structured_output(payload, response_model)
