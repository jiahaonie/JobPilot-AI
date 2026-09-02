"""智能体 API 与模型决策契约。"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentToolDecision(BaseModel):
    """大语言模型生成的一次结构化工具选择。"""

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(BaseModel):
    """发送给工具选择工作流的自然语言指令。"""

    message: str = Field(min_length=1, max_length=2_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message cannot be blank")
        return normalized


class AgentRunResponse(BaseModel):
    """可审计的模型选择及真实处理结果。"""

    selected_tool: str
    arguments: dict[str, Any]
    result: Any
