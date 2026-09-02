"""大语言模型集成异常。"""


class LLMError(Exception):
    """服务商调用与输出错误的基类。"""


class LLMNotConfiguredError(LLMError):
    """未配置 LLM 服务商却调用相关用例时抛出。"""


class StructuredOutputError(LLMError):
    """服务商响应无法满足结构约束时抛出。"""


class LLMTimeoutError(LLMError):
    """服务商未在配置的超时时间内响应时抛出。"""


class LLMRateLimitError(LLMError):
    """服务商限流且重试耗尽时抛出。"""


class LLMProviderError(LLMError):
    """服务商返回 HTTP 或网络错误时抛出。"""
