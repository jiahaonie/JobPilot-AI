"""Validation helper for provider responses."""

from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.exceptions import StructuredOutputError


def parse_structured_output[ModelT: BaseModel](
    payload: Any,
    response_model: type[ModelT],
) -> ModelT:
    """Convert provider data into a Pydantic model or raise a clear error."""

    if isinstance(payload, response_model):
        return payload
    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        raise StructuredOutputError(
            f"LLM output did not match {response_model.__name__}"
        ) from exc
