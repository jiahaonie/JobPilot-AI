"""Replaceable structured LLM client contract."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.exceptions import LLMNotConfiguredError

ModelT = TypeVar("ModelT", bound=BaseModel)


class StructuredLLMClient(Protocol):
    """Port used by services that need validated model output."""

    def complete_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """Complete a prompt and return an instance of response_model."""


class UnavailableLLMClient:
    """Explicit placeholder until a provider adapter is selected."""

    def complete_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """Fail clearly instead of silently returning fabricated data."""

        del prompt, response_model
        raise LLMNotConfiguredError(
            "No LLM provider is configured. Add a provider adapter before analysis."
        )
