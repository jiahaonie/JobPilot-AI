"""供日志记录使用的敏感信息处理辅助函数。"""


def redact_secret(value: str | None, visible_characters: int = 4) -> str:
    """返回适合日志记录且不会暴露完整密钥的表示。"""
    if not value:
        return ""
    if visible_characters < 0:
        raise ValueError("visible_characters must be non-negative")
    if len(value) <= visible_characters:
        return "*" * len(value)
    return value[:visible_characters] + "*" * (len(value) - visible_characters)
