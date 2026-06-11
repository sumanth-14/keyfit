import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InflightJob:
    job_id: str
    user_email: str
    fingerprint: str  # hash of (role_config_id, company, role_title, jd_hash)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InflightTracker:
    """In-memory deduplication tracker for running pipelines.

    Keyed by job_id. A second request with the same fingerprint returns the
    existing job_id instead of starting a new pipeline (Option C from design).
    """

    def __init__(self) -> None:
        self._jobs: dict[str, InflightJob] = {}
        self._by_fingerprint: dict[str, str] = {}  # fingerprint → job_id
        self._results_store: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def find_by_fingerprint(self, fingerprint: str) -> str | None:
        async with self._lock:
            return self._by_fingerprint.get(fingerprint)

    async def acquire(self, job_id: str, user_email: str, fingerprint: str) -> None:
        async with self._lock:
            job = InflightJob(job_id=job_id, user_email=user_email, fingerprint=fingerprint)
            self._jobs[job_id] = job
            self._by_fingerprint[fingerprint] = job_id
        logger.info(f"Pipeline acquired job_id={job_id}")

    async def release(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.pop(job_id, None)
            if job:
                self._by_fingerprint.pop(job.fingerprint, None)
        logger.info(f"Pipeline released job_id={job_id}")

    def is_running(self, job_id: str) -> bool:
        return job_id in self._jobs

    # ── Result storage ─────────────────────────────────────────────────────────
    # Stored here (not in router) so PipelineRunner can write without upward deps.

    def store_result(self, job_id: str, result: dict) -> None:
        self._results_store[job_id] = result

    def get_result(self, job_id: str) -> dict | None:
        return self._results_store.get(job_id)
