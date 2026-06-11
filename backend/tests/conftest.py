import pytest
from pathlib import Path

from app.services.latex_compiler import LatexCompiler
from app.services.temp_storage import TempStorage


@pytest.fixture
def tmp_storage(tmp_path) -> TempStorage:
    return TempStorage(storage_dir=str(tmp_path / "storage"), ttl_seconds=600)


@pytest.fixture
def compiler(tmp_path) -> LatexCompiler:
    return LatexCompiler(work_dir=str(tmp_path / "builds"))


@pytest.fixture
def sample_tex() -> str:
    return (Path(__file__).parent / "fixtures" / "sample.tex").read_text()
