"""小型且可测试的 Agent 工具注册表。"""

from collections.abc import Iterable

from app.agents.tools import ToolSpec
from app.core.exceptions import DomainError


class AgentError(Exception):
    """工具编排错误的基类。"""


class ToolNotFoundError(AgentError):
    """模型请求未注册工具时抛出。"""


class ToolExecutionError(AgentError):
    """已注册工具执行失败时抛出。"""


class ToolRegistry:
    """统一注册工具，并在边界处校验每次调用。"""

    def __init__(self, tools: Iterable[ToolSpec] = ()) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolSpec) -> None:
        """注册或替换具名工具。"""
        if not tool.name.strip():
            raise ValueError("tool name cannot be empty")
        self._tools[tool.name] = tool

    def names(self) -> tuple[str, ...]:
        """返回供模型描述使用的稳定工具名。"""
        return tuple(sorted(self._tools))

    def specs(self) -> tuple[ToolSpec, ...]:
        """按稳定名称顺序返回已注册工具契约。"""
        return tuple(self._tools[name] for name in self.names())

    def execute(self, name: str, payload: object) -> object:
        """校验输入并执行一个明确注册的工具。"""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool {name!r} is not registered")
        try:
            arguments = tool.input_model.model_validate(payload)
            return tool.handler(arguments)
        except (AgentError, DomainError):
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Tool {name!r} failed") from exc
