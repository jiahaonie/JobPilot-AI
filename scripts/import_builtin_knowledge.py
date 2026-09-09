"""将作者审核的电子 PDF 导入独立内置知识集合。"""

import argparse
from pathlib import Path

from app.api.dependencies import build_embedder, build_vector_index
from app.core.config import get_settings
from app.core.database import Database
from app.rag.chunking import TextChunker
from app.rag.parser import PlainTextParser
from app.services.builtin_knowledge import import_builtin_pdf
from app.services.knowledge import KnowledgeDocumentService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="电子 PDF 文件路径")
    args = parser.parse_args()
    pdf_path = args.pdf.resolve(strict=True)
    settings = get_settings()
    database = Database(settings)
    try:
        with database.session() as session:
            service = KnowledgeDocumentService(
                session=session,
                parser=PlainTextParser(),
                chunker=TextChunker(
                    chunk_size=settings.rag_chunk_size,
                    overlap=settings.rag_chunk_overlap,
                ),
                embedder=build_embedder(settings.rag_embedding_model),
                vector_index=build_vector_index(
                    settings.rag_chroma_path,
                    settings.rag_builtin_collection_name,
                ),
            )
            document, created = import_builtin_pdf(
                path=pdf_path,
                service=service,
                embedding_model=settings.rag_embedding_model,
                chunk_size=settings.rag_chunk_size,
                chunk_overlap=settings.rag_chunk_overlap,
            )
            action = "created" if created else "reused"
            print(
                f"{action} built-in document id={document.id} "
                f"chunks={document.chunk_count} source={document.source_name}"
            )
            print(f"Set RAG_BUILTIN_DOCUMENT_IDS={document.id} before generating plans.")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
