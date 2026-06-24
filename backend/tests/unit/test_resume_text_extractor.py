"""Unit tests for deterministic resume text extraction."""
from pathlib import Path

import pytest

from app.models.errors import APIError
from app.services import resume_text_extractor
from app.services.resume_text_extractor import extract_resume_text


class TestLatex:
    async def test_extracts_document_body_only(self):
        tex = (
            rb"\documentclass{article}\usepackage{geometry}"
            rb"\begin{document}John Doe \\ Software Engineer\end{document}"
        )
        text = await extract_resume_text(tex, "tex")
        assert "John Doe" in text
        assert "documentclass" not in text  # preamble dropped
        assert "end{document}" not in text

    async def test_strips_comments(self):
        tex = rb"\begin{document}Real line % a comment here" b"\nNext line\\end{document}"
        text = await extract_resume_text(tex, "tex")
        assert "Real line" in text
        assert "a comment here" not in text

    async def test_handles_tex_without_document_wrapper(self):
        text = await extract_resume_text(b"Just some plain content", "tex")
        assert "Just some plain content" in text

    async def test_empty_latex_raises(self):
        with pytest.raises(APIError):
            await extract_resume_text(rb"\begin{document}\end{document}", "tex")


class TestPdf:
    async def test_extracts_text_via_pdftotext(self, tmp_path, monkeypatch):
        monkeypatch.setattr(resume_text_extractor.settings, "temp_storage_dir", str(tmp_path))

        def fake_run(pdf_path: Path, txt_path: Path, timeout: int = 30):
            Path(txt_path).write_text("Jane Smith\nData Scientist", encoding="utf-8")
            return 0, ""

        monkeypatch.setattr(resume_text_extractor, "_run_pdftotext", fake_run)
        text = await extract_resume_text(b"%PDF-1.4 fake bytes", "pdf")
        assert "Jane Smith" in text

    async def test_pdftotext_failure_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(resume_text_extractor.settings, "temp_storage_dir", str(tmp_path))
        monkeypatch.setattr(
            resume_text_extractor, "_run_pdftotext", lambda *a, **k: (1, "boom")
        )
        with pytest.raises(APIError):
            await extract_resume_text(b"%PDF-1.4", "pdf")

    async def test_scanned_pdf_with_no_text_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(resume_text_extractor.settings, "temp_storage_dir", str(tmp_path))

        def fake_run(pdf_path: Path, txt_path: Path, timeout: int = 30):
            Path(txt_path).write_text("   \n  ", encoding="utf-8")  # whitespace only
            return 0, ""

        monkeypatch.setattr(resume_text_extractor, "_run_pdftotext", fake_run)
        with pytest.raises(APIError):
            await extract_resume_text(b"%PDF-1.4", "pdf")


class TestFormat:
    async def test_unsupported_format_raises(self):
        with pytest.raises(APIError):
            await extract_resume_text(b"data", "docx")
