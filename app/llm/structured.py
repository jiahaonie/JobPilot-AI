"""服务商响应校验辅助函数。"""

from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.exceptions import StructuredOutputError


def parse_structured_output[ModelT: BaseModel](
    payload: Any,
    response_model: type[ModelT],
) -> ModelT:
    """将服务商数据转换为 Pydantic 模型，失败时抛出明确错误。"""
    if isinstance(payload, response_model):
        return payload
    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        raise StructuredOutputError(f"LLM output did not match {response_model.__name__}") from exc
