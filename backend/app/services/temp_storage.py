import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.utils.logging import get_logger

logger = get_logger(__name__)

_PREFIX = "tmp_"


class TempStorage:
    def __init__(self, storage_dir: str, ttl_seconds: int) -> None:
        self.storage_dir = Path(storage_dir)
        self.ttl_seconds = ttl_seconds
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, file_id: str, ext: str = "pdf") -> Path:
        return self.storage_dir / f"{file_id}.{ext}"

    def store(self, data: bytes, ext: str = "pdf") -> str:
        """Store raw bytes and return a tmp_* file_id."""
        file_id = f"{_PREFIX}{uuid.uuid4().hex[:12]}"
        self._path_for(file_id, ext).write_bytes(data)
        logger.info(f"Stored temp file file_id={file_id} bytes={len(data)}")
        return file_id

    def retrieve(self, file_id: str) -> bytes | None:
        """Return bytes for the given file_id, or None if missing/expired."""
        for candidate in self.storage_dir.glob(f"{file_id}.*"):
            return candidate.read_bytes()
        return None

    def delete(self, file_id: str) -> bool:
        deleted = False
        for candidate in self.storage_dir.glob(f"{file_id}.*"):
            candidate.unlink()
            deleted = True
        return deleted

    def get_expiry_iso(self, file_id: str) -> str | None:
        """Return ISO 8601 expiry timestamp for a stored file."""
        for candidate in self.storage_dir.glob(f"{file_id}.*"):
            mtime = candidate.stat().st_mtime
            expiry = datetime.fromtimestamp(mtime + self.ttl_seconds, tz=timezone.utc)
            return expiry.isoformat()
        return None

    def sweep_expired(self) -> int:
        """Delete files older than ttl_seconds. Returns count removed."""
        cutoff = time.time() - self.ttl_seconds
        removed = 0
        for f in self.storage_dir.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        if removed:
            logger.info(f"Swept expired temp files count={removed}")
        return removed
