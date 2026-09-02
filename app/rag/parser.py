"""文档解析端口与首个纯文本适配器。"""

import re

from app.rag.models import ParsedDocument


class PlainTextParser:
    """解析已解码文本，同时保持解析器可替换。"""

    def parse(self, *, document_id: str, source_name: str, text: str) -> ParsedDocument:
        """规范化横向空白，同时保留段落边界。"""
        normalized_newlines = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized_newlines.split("\n")]

        normalized_lines: list[str] = []
        previous_line_was_blank = False
        for line in lines:
            if not line:
                if normalized_lines and not previous_line_was_blank:
                    normalized_lines.append("")
                previous_line_was_blank = True
                continue

            normalized_lines.append(line)
            previous_line_was_blank = False

        normalized = "\n".join(normalized_lines).strip()
        if not normalized:
            raise ValueError("document text cannot be empty")
        return ParsedDocument(
            document_id=document_id,
            source_name=source_name,
            text=normalized,
        )
