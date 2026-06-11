import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from app.utils.logging import get_logger

logger = get_logger(__name__)

_KEEPALIVE_INTERVAL = 15.0  # seconds between keepalive pings
_QUEUE_MAXSIZE = 256

# Sentinel placed in queue when pipeline is done
_STREAM_DONE = object()


class SseEmitter:
    """Per-job SSE event broadcaster.

    pipeline_runner calls emit(); the router's streaming endpoint reads from
    subscribe() as an async generator.
    """

    def __init__(self) -> None:
        # job_id → asyncio.Queue of formatted SSE strings
        self._queues: dict[str, asyncio.Queue] = {}

    def _ensure_queue(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        return self._queues[job_id]

    async def emit(self, job_id: str, event: str, data: dict) -> None:
        """Push one SSE event into the job's queue."""
        queue = self._ensure_queue(job_id)
        payload = json.dumps({**data, "timestamp": datetime.now(timezone.utc).isoformat()})
        message = f"event: {event}\ndata: {payload}\n\n"
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for job_id={job_id} — dropping event={event}")

    async def close(self, job_id: str) -> None:
        """Signal that the pipeline is finished — consumer will stop iterating."""
        queue = self._ensure_queue(job_id)
        await queue.put(_STREAM_DONE)

    async def subscribe(self, job_id: str) -> AsyncGenerator[str, None]:
        """Async generator that yields SSE-formatted strings for the given job.

        Sends keepalive comments every 15s to prevent proxy timeouts.
        """
        queue = self._ensure_queue(job_id)
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_INTERVAL)
                if item is _STREAM_DONE:
                    self._queues.pop(job_id, None)
                    return
                yield item
            except asyncio.TimeoutError:
                # SSE comment — keeps connection alive through proxies
                yield ":keepalive\n\n"

    def remove(self, job_id: str) -> None:
        self._queues.pop(job_id, None)
