import asyncio
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.models.latex import CompileError
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompileResult:
    success: bool
    pdf_bytes: bytes | None = None
    pages: int | None = None
    errors: list[CompileError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compile_log: str = ""


def _run_pdflatex(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    """Run pdflatex synchronously. Called from a thread executor."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # prevent any dialog waiting for input
            timeout=timeout,
        )
        return result.returncode, result.stdout.decode(errors="replace")
    except subprocess.TimeoutExpired:
        return -1, "pdflatex timed out"


def _run_pdfinfo(pdf_path: Path, timeout: int = 10) -> str:
    """Run pdfinfo synchronously. Called from a thread executor."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return result.stdout.decode(errors="replace")
    except Exception:
        return ""


class LatexCompiler:
    def __init__(self, work_dir: str) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def compile(self, tex_source: str, filename: str = "resume") -> CompileResult:
        """Compile LaTeX source to PDF. Returns CompileResult with pdf_bytes on success."""
        build_dir = self.work_dir / f"build_{uuid.uuid4().hex[:8]}"
        build_dir.mkdir(parents=True)
        try:
            return await self._run_compile(tex_source, filename, build_dir)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

    async def _run_compile(
        self, tex_source: str, filename: str, build_dir: Path
    ) -> CompileResult:
        tex_file = build_dir / f"{filename}.tex"
        pdf_file = build_dir / f"{filename}.pdf"
        log_file = build_dir / f"{filename}.log"

        tex_file.write_text(tex_source, encoding="utf-8")

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={build_dir}",
            str(tex_file),
        ]

        loop = asyncio.get_event_loop()

        # Two passes so cross-references (table of contents etc.) resolve correctly
        for pass_num in range(1, 3):
            returncode, stdout_text = await loop.run_in_executor(
                None, _run_pdflatex, cmd, 60
            )

            if returncode == -1:
                return CompileResult(
                    success=False,
                    errors=[CompileError(type="timeout", message="pdflatex timed out after 60s")],
                )

            if returncode != 0:
                log_text = (
                    log_file.read_text(encoding="utf-8", errors="replace")
                    if log_file.exists()
                    else stdout_text
                )
                logger.warning(f"pdflatex pass {pass_num} failed returncode={returncode}")
                return CompileResult(
                    success=False,
                    errors=_parse_errors(log_text),
                    compile_log=_tail_log(log_text),
                )

        if not pdf_file.exists():
            return CompileResult(
                success=False,
                errors=[CompileError(type="no_output", message="pdflatex exited 0 but produced no PDF")],
            )

        pdf_bytes = pdf_file.read_bytes()
        log_text = (
            log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
        )
        pages = await self._page_count(pdf_file)

        return CompileResult(
            success=True,
            pdf_bytes=pdf_bytes,
            pages=pages,
            warnings=_parse_warnings(log_text),
            compile_log=_tail_log(log_text),
        )

    async def _page_count(self, pdf_path: Path) -> int:
        """Use pdfinfo to count pages. Falls back to 1 on any error."""
        loop = asyncio.get_event_loop()
        try:
            output = await loop.run_in_executor(None, _run_pdfinfo, pdf_path, 10)
            for line in output.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
        except Exception as exc:
            logger.warning(f"pdfinfo failed: {exc}")
        return 1

    async def compile_one_page(
        self, tex_source: str, filename: str = "resume"
    ) -> CompileResult:
        """Compile and enforce one-page output.

        Phase 1 stub — returns PAGE_FIT_FAILED if output exceeds one page.
        Full trim ladder (walks bullet counts across roles) is wired in Phase 3
        once the latex assembler exists.
        """
        result = await self.compile(tex_source, filename)
        if not result.success:
            return result
        if result.pages and result.pages > 1:
            return CompileResult(
                success=False,
                errors=[
                    CompileError(
                        type="page_overflow",
                        message=f"Resume is {result.pages} pages; must fit on one page.",
                    )
                ],
                compile_log=result.compile_log,
            )
        return result


# ── Log parsing helpers ────────────────────────────────────────────────────────

_ERROR_RE = re.compile(r"^!\s+(.+)$", re.MULTILINE)
_LINE_RE = re.compile(r"l\.(\d+)")


def _parse_errors(log_text: str) -> list[CompileError]:
    errors: list[CompileError] = []
    for m in _ERROR_RE.finditer(log_text):
        message = m.group(1).strip()

        if "undefined control sequence" in message.lower():
            err_type = "undefined_control_sequence"
        elif "missing" in message.lower():
            err_type = "missing_token"
        else:
            err_type = "latex_error"

        surrounding = log_text[m.start() : m.start() + 300]
        lm = _LINE_RE.search(surrounding)
        line_num = int(lm.group(1)) if lm else None

        errors.append(CompileError(line=line_num, type=err_type, message=message))

    return errors[:10]


def _parse_warnings(log_text: str) -> list[str]:
    return [
        line.strip()
        for line in log_text.splitlines()
        if "Warning" in line and not line.startswith("!")
    ][:20]


def _tail_log(log_text: str, lines: int = 50) -> str:
    return "\n".join(log_text.splitlines()[-lines:])
