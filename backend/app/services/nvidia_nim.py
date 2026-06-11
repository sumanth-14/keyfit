import asyncio

import httpx

from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 120.0
_MAX_ATTEMPTS = 4


class NimClient:
    """Async client for the NVIDIA NIM (OpenAI-compatible) API.

    Retries up to 4 attempts:
      - 429: wait 15s × attempt number, then retry
      - 5xx: wait 10s, then retry
      - timeout (90s): one retry immediately
    """

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        agent_name: str = "",
    ) -> str:
        """Send a chat completion request and return the assistant message text.

        `agent_name` is accepted for interface parity with MockNimClient (which
        uses it to pick a canned response) and is ignored by the real client.
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

                if resp.status_code == 401:
                    raise APIError(
                        ErrorCode.NIM_KEY_INVALID,
                        "NVIDIA NIM API key was rejected. Please check your key.",
                        retry_possible=False,
                    )

                if resp.status_code == 429:
                    wait = 15.0 * attempt
                    logger.warning(
                        f"NIM rate limited attempt={attempt} waiting={wait}s"
                    )
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(wait)
                        last_exc = APIError(
                            ErrorCode.NIM_RATE_LIMITED,
                            "NVIDIA NIM rate limit hit. Retrying...",
                            retry_possible=True,
                        )
                        continue
                    raise APIError(
                        ErrorCode.NIM_RATE_LIMITED,
                        "NVIDIA NIM is rate limiting requests. Please try again in a minute.",
                        retry_possible=True,
                    )

                if resp.status_code >= 500:
                    logger.warning(
                        f"NIM server error status={resp.status_code} attempt={attempt}"
                    )
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(10.0)
                        last_exc = APIError(
                            ErrorCode.NIM_MODEL_UNAVAILABLE,
                            "NVIDIA NIM returned a server error. Retrying...",
                            retry_possible=True,
                        )
                        continue
                    raise APIError(
                        ErrorCode.NIM_MODEL_UNAVAILABLE,
                        "NVIDIA NIM is currently unavailable. Please try again later.",
                        retry_possible=True,
                    )

                # Unexpected status
                raise APIError(
                    ErrorCode.INTERNAL_ERROR,
                    f"Unexpected response from NIM: HTTP {resp.status_code}",
                    retry_possible=True,
                )

            except httpx.TimeoutException as exc:
                logger.warning(f"NIM request timed out attempt={attempt}")
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    continue  # one immediate retry on timeout
                raise APIError(
                    ErrorCode.NIM_MODEL_UNAVAILABLE,
                    "NVIDIA NIM request timed out. Please try again.",
                    retry_possible=True,
                ) from exc

            except APIError:
                raise
            except Exception as exc:
                raise APIError(
                    ErrorCode.INTERNAL_ERROR,
                    "Unexpected error communicating with NVIDIA NIM.",
                    retry_possible=True,
                ) from exc

        # Should be unreachable, but satisfy type checker
        raise APIError(
            ErrorCode.NIM_MODEL_UNAVAILABLE,
            "NVIDIA NIM request failed after all retries.",
            retry_possible=True,
        )
