"""可替换 RAG 边界的单元测试。"""

import pytest

from app.rag.chunking import TextChunker
from app.rag.models import ParsedDocument
from app.rag.parser import PlainTextParser
from app.rag.retrieval import LexicalRetriever


def test_plain_text_is_normalized_and_chunked() -> None:
    parser = PlainTextParser()
    document = parser.parse(
        document_id="doc-1",
        source_name="notes.txt",
        text="FastAPI   dependency injection makes boundaries testable.",
    )

    chunks = TextChunker(chunk_size=24, overlap=5).chunk(document)

    assert document.text == "FastAPI dependency injection makes boundaries testable."
    assert len(chunks) >= 2
    assert all(chunk.document_id == "doc-1" for chunk in chunks)


def test_parser_preserves_markdown_paragraph_boundaries() -> None:
    parser = PlainTextParser()

    document = parser.parse(
        document_id="doc-1",
        source_name="fastapi-notes.md",
        text="# FastAPI\r\n\r\n\r\n依赖注入   使用 Depends。\r\n\r\n测试使用 pytest。",
    )

    assert document.text == ("# FastAPI\n\n依赖注入 使用 Depends。\n\n测试使用 pytest。")


def test_chunker_prefers_chinese_semicolon_boundary() -> None:
    document = ParsedDocument(
        document_id="doc-1", source_name="notes.txt", text="第一部分；第二部分内容很长"
    )

    chunks = TextChunker(chunk_size=8, overlap=0).chunk(document)

    assert chunks[0].text == "第一部分；"
    assert chunks[1].text == "第二部分内容很长"


def test_chunker_prefers_paragraph_boundary() -> None:
    document = ParsedDocument(
        document_id="doc-1",
        source_name="fastapi-notes.md",
        text="第一段介绍 FastAPI。\n\n第二段介绍依赖注入和测试方法。",
    )

    chunks = TextChunker(chunk_size=24, overlap=0).chunk(document)

    assert chunks[0].text == "第一段介绍 FastAPI。"
    assert chunks[1].text == "第二段介绍依赖注入和测试方法。"


def test_chunker_keeps_requested_overlap() -> None:
    document = ParsedDocument(
        document_id="doc-1",
        source_name="notes.txt",
        text="abcdefghij",
    )

    chunks = TextChunker(chunk_size=6, overlap=2).chunk(document)

    assert [chunk.text for chunk in chunks] == ["abcdef", "efghij"]


def test_lexical_retriever_returns_matching_chunks() -> None:
    document = ParsedDocument(
        document_id="doc-1",
        source_name="notes.txt",
        text="FastAPI dependency injection makes boundaries testable.",
    )
    chunks = TextChunker(chunk_size=100, overlap=0).chunk(document)

    results = LexicalRetriever().retrieve(chunks, "dependency injection")

    assert len(results) == 1
    assert results[0].score == 1.0


def test_chunker_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        TextChunker(chunk_size=10, overlap=10)
