"""Unit tests for LatexCompiler — subprocess calls are mocked.

The compiler delegates to the module-level `_run_pdflatex` / `_run_pdfinfo`
helpers (which call `subprocess.run` in a thread executor), so we patch those
rather than the subprocess API directly.
"""
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.latex import CompileError
from app.services.latex_compiler import (
    LatexCompiler,
    CompileResult,
    _parse_errors,
    _parse_warnings,
    _tail_log,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

FAKE_PDF = b"%PDF-1.4 fake-content"


def _output_dir(cmd: list[str]) -> Path:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("-output-directory="):
            return Path(arg.split("=", 1)[1])
    raise AssertionError("no -output-directory= in pdflatex cmd")


def _tex_stem(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.endswith(".tex"):
            return Path(arg).stem
    return "resume"


@contextmanager
def _patch_pdflatex(returncode: int = 0, log: str = "", pages: int = 1):
    """Patch the compiler's pdflatex/pdfinfo helpers with fakes."""

    def _pdflatex(cmd, timeout=60):
        out_dir = _output_dir(cmd)
        stem = _tex_stem(cmd)
        if returncode == 0:
            (out_dir / f"{stem}.pdf").write_bytes(FAKE_PDF)
        (out_dir / f"{stem}.log").write_text(log)
        return returncode, log

    def _pdfinfo(pdf_path, timeout=10):
        return f"Pages:          {pages}\n"

    with patch("app.services.latex_compiler._run_pdflatex", _pdflatex), patch(
        "app.services.latex_compiler._run_pdfinfo", _pdfinfo
    ):
        yield


# ── TempStorage unit tests ─────────────────────────────────────────────────────

class TestTempStorage:
    def test_store_and_retrieve(self, tmp_storage):
        data = b"hello pdf"
        file_id = tmp_storage.store(data)
        assert file_id.startswith("tmp_")
        assert tmp_storage.retrieve(file_id) == data

    def test_retrieve_missing_returns_none(self, tmp_storage):
        assert tmp_storage.retrieve("tmp_doesnotexist") is None

    def test_delete(self, tmp_storage):
        file_id = tmp_storage.store(b"data")
        assert tmp_storage.delete(file_id) is True
        assert tmp_storage.retrieve(file_id) is None

    def test_delete_missing_returns_false(self, tmp_storage):
        assert tmp_storage.delete("tmp_ghost") is False

    def test_sweep_expired(self, tmp_storage, tmp_path):
        # Create a storage with very short TTL
        from app.services.temp_storage import TempStorage
        short_storage = TempStorage(str(tmp_path / "short"), ttl_seconds=0)
        short_storage.store(b"data")
        time.sleep(0.01)
        removed = short_storage.sweep_expired()
        assert removed == 1

    def test_sweep_keeps_fresh_files(self, tmp_storage):
        tmp_storage.store(b"fresh")
        removed = tmp_storage.sweep_expired()
        assert removed == 0

    def test_expiry_iso_format(self, tmp_storage):
        file_id = tmp_storage.store(b"data")
        expiry = tmp_storage.get_expiry_iso(file_id)
        assert expiry is not None
        assert "T" in expiry  # ISO 8601

    def test_expiry_missing_returns_none(self, tmp_storage):
        assert tmp_storage.get_expiry_iso("tmp_ghost") is None


# ── LatexCompiler unit tests ───────────────────────────────────────────────────

class TestLatexCompilerSuccess:
    async def test_compile_success_returns_pdf_bytes(self, compiler):
        with _patch_pdflatex():
            result = await compiler.compile("\\documentclass{article}\\begin{document}Hi\\end{document}")

        assert result.success is True
        assert result.pdf_bytes == FAKE_PDF
        assert result.pages == 1

    async def test_compile_uses_filename_hint(self, tmp_path):
        comp = LatexCompiler(work_dir=str(tmp_path / "builds"))
        seen_files: list[str] = []

        def _pdflatex(cmd, timeout=60):
            seen_files.append(f"{_tex_stem(cmd)}.tex")
            out_dir = _output_dir(cmd)
            stem = _tex_stem(cmd)
            (out_dir / f"{stem}.pdf").write_bytes(FAKE_PDF)
            (out_dir / f"{stem}.log").write_text("")
            return 0, ""

        def _pdfinfo(pdf_path, timeout=10):
            return "Pages:          1\n"

        with patch("app.services.latex_compiler._run_pdflatex", _pdflatex), patch(
            "app.services.latex_compiler._run_pdfinfo", _pdfinfo
        ):
            result = await comp.compile("tex", filename="myresume")

        assert result.success is True
        assert any("myresume.tex" in f for f in seen_files)

    async def test_compile_cleans_up_build_dir(self, tmp_path):
        comp = LatexCompiler(work_dir=str(tmp_path / "builds"))
        with _patch_pdflatex():
            await comp.compile("tex")
        # build_* subdirs should be gone after compile
        build_dirs = list(Path(str(tmp_path / "builds")).glob("build_*"))
        assert len(build_dirs) == 0


class TestLatexCompilerFailure:
    async def test_compile_failure_on_nonzero_exit(self, compiler):
        log = "! Undefined control sequence.\nl.5 \\badcmd\n"
        with _patch_pdflatex(returncode=1, log=log):
            result = await compiler.compile("bad tex")

        assert result.success is False
        assert len(result.errors) >= 1
        assert result.errors[0].type == "undefined_control_sequence"

    async def test_compile_failure_carries_line_number(self, compiler):
        log = "! Undefined control sequence.\nl.42 \\ohno\n"
        with _patch_pdflatex(returncode=1, log=log):
            result = await compiler.compile("bad tex")

        assert result.errors[0].line == 42

    async def test_compile_timeout_returns_error(self, compiler):
        # _run_pdflatex returns (-1, ...) on TimeoutExpired.
        def _timeout(cmd, timeout=60):
            return -1, "pdflatex timed out"

        with patch("app.services.latex_compiler._run_pdflatex", _timeout):
            result = await compiler.compile("tex")

        assert result.success is False
        assert result.errors[0].type == "timeout"


class TestCompileOnePage:
    async def test_one_page_passes(self, compiler):
        with _patch_pdflatex(pages=1):
            result = await compiler.compile_one_page("tex")
        assert result.success is True

    async def test_two_page_fails(self, compiler):
        with _patch_pdflatex(pages=2):
            result = await compiler.compile_one_page("tex")

        assert result.success is False
        assert result.errors[0].type == "page_overflow"


# ── Log parsing unit tests ─────────────────────────────────────────────────────

class TestLogParsing:
    def test_parse_errors_empty_log(self):
        assert _parse_errors("") == []

    def test_parse_errors_undefined_cs(self):
        log = "! Undefined control sequence.\nl.5 \\badcmd\n"
        errors = _parse_errors(log)
        assert len(errors) == 1
        assert errors[0].type == "undefined_control_sequence"
        assert errors[0].line == 5

    def test_parse_errors_missing_token(self):
        log = "! Missing } inserted.\nl.10\n"
        errors = _parse_errors(log)
        assert errors[0].type == "missing_token"

    def test_parse_errors_generic(self):
        log = "! Some other error.\nl.3\n"
        errors = _parse_errors(log)
        assert errors[0].type == "latex_error"

    def test_parse_errors_capped_at_ten(self):
        log = "\n".join(f"! Error {i}.\nl.{i}\n" for i in range(20))
        assert len(_parse_errors(log)) == 10

    def test_parse_warnings_extracts_lines(self):
        log = "LaTeX Warning: something.\nLaTeX Warning: other thing.\n"
        warnings = _parse_warnings(log)
        assert len(warnings) == 2

    def test_parse_warnings_excludes_error_lines(self):
        log = "! Error line with Warning in it.\n"
        assert _parse_warnings(log) == []

    def test_tail_log_returns_last_n_lines(self):
        log = "\n".join(str(i) for i in range(100))
        tail = _tail_log(log, lines=10)
        assert tail.startswith("90")
        assert "99" in tail
