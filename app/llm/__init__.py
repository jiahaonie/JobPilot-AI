"""大语言模型集成边界。"""

from app.llm.client import StructuredLLMClient, UnavailableLLMClient
from app.llm.deepseek_client import DeepSeekStructuredClient

__all__ = [
    "DeepSeekStructuredClient",
    "StructuredLLMClient",
    "UnavailableLLMClient",
]
