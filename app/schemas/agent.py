"""Agent API and model-decision contracts."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentToolDecision(BaseModel):
    """One structured tool selection made by the LLM."""

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(BaseModel):
    """Natural-language instruction sent to the tool-selection workflow."""

    message: str = Field(min_length=1, max_length=2_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message cannot be blank")
        return normalized


class AgentRunResponse(BaseModel):
    """Auditable model choice plus the real handler result."""

    selected_tool: str
    arguments: dict[str, Any]
    result: Any
