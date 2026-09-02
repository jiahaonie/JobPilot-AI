"""不耦合 LLM 的简历文件上传 HTTP 测试。"""

from tests.unit.test_resume_file import make_electronic_pdf


def test_uploads_markdown_and_saves_pending_resume(client) -> None:
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.md", "# 技能\n\nPython".encode(), "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "resume"
    assert body["raw_text"] == "# 技能\n\nPython"
    assert body["skills"] == []
    assert body["analysis_status"] == "pending"


def test_upload_rejects_unsupported_file(client) -> None:
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.docx", b"not docx", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_uploads_electronic_pdf(client) -> None:
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", make_electronic_pdf(), "application/pdf")},
    )

    assert response.status_code == 201
    assert "Python FastAPI" in response.json()["raw_text"]
    assert response.json()["analysis_status"] == "pending"


def test_upload_rejects_non_utf8_text(client) -> None:
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"\xff\xfe", "text/plain")},
    )

    assert response.status_code == 422
