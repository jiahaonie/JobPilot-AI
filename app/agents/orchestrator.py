"""Small, testable agent tool registry."""

from collections.abc import Iterable

from app.agents.tools import ToolSpec


class AgentError(Exception):
    """Base class for tool orchestration errors."""


class ToolNotFoundError(AgentError):
    """Raised when a model requests an unregistered tool."""


class ToolExecutionError(AgentError):
    """Raised when a registered tool fails during execution."""


class ToolRegistry:
    """Register tools once and validate every invocation at the boundary."""

    def __init__(self, tools: Iterable[ToolSpec] = ()) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolSpec) -> None:
        """Register or replace a named tool."""

        if not tool.name.strip():
            raise ValueError("tool name cannot be empty")
        self._tools[tool.name] = tool

    def names(self) -> tuple[str, ...]:
        """Return stable tool names for model-facing descriptions."""

        return tuple(sorted(self._tools))

    def specs(self) -> tuple[ToolSpec, ...]:
        """Return registered tool contracts in stable name order."""

        return tuple(self._tools[name] for name in self.names())

    def execute(self, name: str, payload: object) -> object:
        """Validate input and execute one explicitly registered tool."""

        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool {name!r} is not registered")
        try:
            arguments = tool.input_model.model_validate(payload)
            return tool.handler(arguments)
        except AgentError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Tool {name!r} failed") from exc


class AgentOrchestrator:
    """Application-facing facade around the tool registry."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute_tool(self, name: str, payload: object) -> object:
        """Execute a tool through the validated registry boundary."""

        return self.registry.execute(name, payload)
