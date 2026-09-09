"""作者维护的电子 PDF 内置资料导入流程。"""

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from app.models.knowledge_document import KnowledgeDocument
from app.repositories.knowledge_document import KnowledgeDocumentRepository
from app.services.knowledge import KnowledgeDocumentService


def extract_electronic_pdf(path: Path) -> str:
    """提取电子 PDF 正文，并拒绝加密或没有可用文本的文件。"""
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("encrypted PDFs are not supported")
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        normalized = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n"))
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if normalized:
            pages.append(normalized)
    if not pages:
        raise ValueError("PDF did not contain extractable text")
    return "\n\n".join(pages)


def import_builtin_pdf(
    *,
    path: Path,
    service: KnowledgeDocumentService,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[KnowledgeDocument, bool]:
    """幂等导入一份已由作者确认用途的内置 PDF。"""
    source_bytes = path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    repository = KnowledgeDocumentRepository(service.session)
    existing = repository.get_ready_builtin_by_fingerprint(
        source_sha256=source_sha256,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if existing is not None:
        return existing, False

    text = extract_electronic_pdf(path)
    document = service.create(
        source_name=path.name,
        content_type="application/pdf",
        raw_text=text,
        is_builtin=True,
        approved=True,
        source_sha256=source_sha256,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return document, True
