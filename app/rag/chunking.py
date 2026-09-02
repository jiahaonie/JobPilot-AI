"""确定性文本分块。"""

from app.rag.models import DocumentChunk, ParsedDocument


class TextChunker:
    """感知边界且重叠范围确定的字符分块器。"""

    _BOUNDARIES = ("\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", ";", " ")

    def __init__(self, *, chunk_size: int = 800, overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        """将规范化文档拆分为长度受限且相互重叠的分块。"""
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                end = self._find_boundary(text, start=start, end=end)
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    DocumentChunk(
                        document_id=document.document_id,
                        source_name=document.source_name,
                        chunk_index=chunk_index,
                        text=piece,
                    )
                )
                chunk_index += 1
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return chunks

    def _find_boundary(self, text: str, *, start: int, end: int) -> int:
        """优先选择分块窗口后半段的语义边界。"""
        earliest_boundary = start + self.chunk_size // 2
        for separator in self._BOUNDARIES:
            boundary = text.rfind(separator, earliest_boundary, end)
            if boundary != -1:
                return boundary + len(separator)
        return end
