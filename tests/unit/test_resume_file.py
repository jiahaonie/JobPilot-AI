"""Unit tests for supported resume file extraction."""

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.core.exceptions import InvalidFileError, UnsupportedFileTypeError
from app.services.resume_file import ResumeFileService


def make_electronic_pdf(text: str = "Python FastAPI") -> bytes:
    """Build a minimal electronic PDF with an extractable text layer."""

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def service() -> ResumeFileService:
    return ResumeFileService(
        max_upload_bytes=1024 * 1024,
        max_pdf_pages=5,
        max_text_chars=10_000,
    )


@pytest.mark.parametrize("filename", ["resume.txt", "resume.md"])
def test_parses_utf8_text_formats(service, filename) -> None:
    parsed = service.parse(
        filename=filename,
        content="熟悉 Python 和 FastAPI。".encode(),
    )

    assert parsed.source_name == filename
    assert parsed.raw_text == "熟悉 Python 和 FastAPI。"


def test_parses_electronic_pdf(service) -> None:
    parsed = service.parse(filename="resume.pdf", content=make_electronic_pdf())

    assert "Python FastAPI" in parsed.raw_text


def test_rejects_scanned_or_empty_pdf(service) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)

    with pytest.raises(InvalidFileError, match="scanned PDFs"):
        service.parse(filename="scan.pdf", content=output.getvalue())


def test_rejects_damaged_pdf(service) -> None:
    with pytest.raises(InvalidFileError, match="damaged"):
        service.parse(filename="resume.pdf", content=b"%PDF-not-valid")


def test_rejects_unsupported_extension(service) -> None:
    with pytest.raises(UnsupportedFileTypeError):
        service.parse(filename="resume.docx", content=b"document")
