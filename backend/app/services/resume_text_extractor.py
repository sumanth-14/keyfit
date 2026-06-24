"""Deterministic resume text extraction (no LLM).

Turns an uploaded file into plain text the parser agent can structure:
  - PDF  -> `pdftotext` (poppler, already in the image; no new dependency)
  - LaTeX -> decode + strip preamble/comments

This is the reliable half of parsing. Understanding the text (which line is a
title vs a bullet, etc.) is left to the AI agent downstream.
"""
import asyncio
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from app.config import settings
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Matches an unescaped `%` and the rest of its line (a LaTeX comment).
_LATEX_COMMENT_RE = re.compile(r"(?<!\\)%.*")


def _run_pdftotext(pdf_path: Path, txt_path: Path, timeout: int = 30) -> tuple[int, str]:
    """Run pdftotext synchronously. Called from a thread executor.

    `-layout` keeps the visual reading order, which matters for multi-column
    resumes. Returns (returncode, stdout_or_message).
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
        return result.returncode, result.stdout.decode(errors="replace")
    except subprocess.TimeoutExpired:
        return -1, "pdftotext timed out"
    except FileNotFoundError:
        return -2, "pdftotext not installed"


async def extract_resume_text(content: bytes, fmt: str) -> str:
    """Extract plain text from an uploaded resume. `fmt` is 'pdf' or 'tex'."""
    normalized = (fmt or "").lower().lstrip(".")
    if normalized == "pdf":
        return await _extract_pdf(content)
    if normalized in ("tex", "latex"):
        return _extract_latex(content)
    raise APIError(
        ErrorCode.INTERNAL_ERROR,
        f"Unsupported resume format '{fmt}'. Please upload a .tex or .pdf file.",
        retry_possible=False,
    )


def _extract_latex(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")

    # Keep only the document body — the preamble (packages, macro defs) is pure
    # noise for extraction and wastes the model's input budget.
    begin = text.find(r"\begin{document}")
    if begin != -1:
        text = text[begin + len(r"\begin{document}") :]
    end = text.find(r"\end{document}")
    if end != -1:
        text = text[:end]

    text = _LATEX_COMMENT_RE.sub("", text).strip()
    if not text:
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            "Could not read any text from the LaTeX file.",
            retry_possible=False,
        )
    return text


async def _extract_pdf(content: bytes) -> str:
    work_dir = Path(settings.temp_storage_dir) / f"pdf_{uuid.uuid4().hex[:8]}"
    work_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = work_dir / "resume.pdf"
    txt_path = work_dir / "resume.txt"
    try:
        pdf_path.write_bytes(content)
        loop = asyncio.get_event_loop()
        returncode, message = await loop.run_in_executor(
            None, _run_pdftotext, pdf_path, txt_path, 30
        )
        if returncode != 0:
            logger.warning(f"pdftotext failed returncode={returncode} message={message!r}")
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "Could not read the PDF. Please try a different export, or upload your .tex file.",
                retry_possible=False,
            )

        text = (
            txt_path.read_text(encoding="utf-8", errors="replace").strip()
            if txt_path.exists()
            else ""
        )
        if not text:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "This PDF has no selectable text (it may be scanned or image-based). "
                "Please upload a text-based PDF or your .tex file.",
                retry_possible=False,
            )
        return text
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
