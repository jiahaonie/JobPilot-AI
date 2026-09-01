"""Validate uploaded resume files and extract normalized text."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)

_TEXT_SUFFIXES = {".txt", ".md"}
_PDF_SUFFIX = ".pdf"


@dataclass(frozen=True, slots=True)
class ParsedResumeFile:
    """Safe filename and text extracted from one supported upload."""

    source_name: str
    raw_text: str


class ResumeFileService:
    """Convert TXT, Markdown, or electronic PDF bytes into resume text."""

    def __init__(
        self,
        *,
        max_upload_bytes: int,
        max_pdf_pages: int,
        max_text_chars: int,
    ) -> None:
        self.max_upload_bytes = max_upload_bytes
        self.max_pdf_pages = max_pdf_pages
        self.max_text_chars = max_text_chars

    def parse(self, *, filename: str | None, content: bytes) -> ParsedResumeFile:
        """Validate one upload and return non-empty normalized text."""

        source_name = Path(filename or "").name.strip()
        if not source_name:
            raise InvalidFileError("uploaded resume must have a filename")
        if len(content) > self.max_upload_bytes:
            raise FileTooLargeError(
                f"resume exceeds {self.max_upload_bytes} bytes"
            )

        suffix = Path(source_name).suffix.lower()
        if suffix in _TEXT_SUFFIXES:
            raw_text = self._parse_utf8(content)
        elif suffix == _PDF_SUFFIX:
            raw_text = self._parse_pdf(content)
        else:
            raise UnsupportedFileTypeError(
                "only .txt, .md, and electronic .pdf resumes are supported"
            )

        normalized = raw_text.strip()
        if not normalized:
            raise InvalidFileError("resume text cannot be empty")
        if len(normalized) > self.max_text_chars:
            raise InvalidFileError(
                f"extracted resume text exceeds {self.max_text_chars} characters"
            )
        return ParsedResumeFile(source_name=source_name, raw_text=normalized)

    @staticmethod
    def _parse_utf8(content: bytes) -> str:
        """Decode UTF-8 text while accepting an optional byte-order mark."""

        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidFileError("TXT and Markdown resumes must be valid UTF-8") from exc

    def _parse_pdf(self, content: bytes) -> str:
        """Extract text from an electronic PDF; scanned PDFs are rejected."""

        if not content.startswith(b"%PDF-"):
            raise InvalidFileError("uploaded file is not a valid PDF")
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise InvalidFileError("encrypted PDF resumes are not supported")
            if len(reader.pages) > self.max_pdf_pages:
                raise InvalidFileError(
                    f"PDF resume exceeds {self.max_pdf_pages} pages"
                )
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except InvalidFileError:
            raise
        except (FileNotDecryptedError, PdfReadError, ValueError) as exc:
            raise InvalidFileError("PDF resume is damaged or cannot be parsed") from exc

        if not text.strip():
            raise InvalidFileError(
                "PDF contains no extractable text; scanned PDFs are not supported"
            )
        return text
