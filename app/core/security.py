"""Security helpers shared by future authentication and observability code."""


def redact_secret(value: str | None, visible_characters: int = 4) -> str:
    """Return a log-safe representation without exposing a complete secret."""

    if not value:
        return ""
    if visible_characters < 0:
        raise ValueError("visible_characters must be non-negative")
    if len(value) <= visible_characters:
        return "*" * len(value)
    return value[:visible_characters] + "*" * (len(value) - visible_characters)
