"""可替换的结构化 LLM 客户端契约。"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.exceptions import LLMNotConfiguredError

ModelT = TypeVar("ModelT", bound=BaseModel)


class StructuredLLMClient(Protocol):
    """需要已校验模型输出的服务所使用的端口。"""

    def complete_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """完成提示词请求并返回指定响应模型的实例。"""


class UnavailableLLMClient:
    """选择服务商适配器前使用的明确占位实现。"""

    def complete_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """明确失败，不静默返回伪造数据。"""
        del prompt, response_model
        raise LLMNotConfiguredError(
            "No LLM provider is configured. Add a provider adapter before analysis."
        )
