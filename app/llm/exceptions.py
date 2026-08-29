"""LLM integration errors."""


class LLMError(Exception):
    """Base class for provider and output errors."""


class LLMNotConfiguredError(LLMError):
    """Raised when an LLM use case is called without a provider adapter."""


class StructuredOutputError(LLMError):
    """Raised when a provider response cannot satisfy its schema."""


class LLMTimeoutError(LLMError):
    """Raised when the provider does not answer within the configured timeout."""


class LLMRateLimitError(LLMError):
    """Raised when the provider signals a rate limit, before a retry is exhausted."""
