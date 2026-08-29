"""Document parsing ports and the first plain-text adapter."""

import re

from app.rag.models import ParsedDocument


class PlainTextParser:
    """Parse already-decoded text while keeping the parser replaceable."""

    def parse(self, *, document_id: str, source_name: str, text: str) -> ParsedDocument:
        """Normalize horizontal whitespace while preserving paragraph boundaries."""

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
