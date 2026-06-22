from abc import ABC, abstractmethod

from app.services.nvidia_nim import NimClient
from app.services.nvidia_nim_mock import MockNimClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias accepted by all agent constructors
AnyNimClient = NimClient | MockNimClient


class Agent(ABC):
    """Base class for all LLM agents. One LLM call per agent (Rule 4)."""

    name: str = ""  # stable agent id (used by MockNimClient to pick a canned response)
    temperature: float = 0.3
    max_tokens: int = 2048
    # Per-call NIM budget. None → use the client's default retry ladder. A
    # latency-sensitive agent can tighten these to fail fast (see ResumeParserAgent).
    request_timeout: float | None = None
    max_attempts: int | None = None
    # Optional API response_format, e.g. {"type": "json_object"} to force valid JSON.
    response_format: dict | None = None

    def __init__(self, nim_client: AnyNimClient, model: str) -> None:
        self.nim = nim_client
        self.model = model

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def user_prompt(self, **inputs) -> str: ...

    @abstractmethod
    def parse_response(self, raw: str) -> dict: ...

    async def run(self, **inputs) -> dict:
        """Execute the agent: build prompts, call NIM, parse response."""
        system = self.system_prompt()
        user = self.user_prompt(**inputs)
        logger.info(f"Agent {self.__class__.__name__} running model={self.model}")
        raw = await self.nim.complete(
            model=self.model,
            system=system,
            user=user,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            agent_name=self.name,
            timeout=self.request_timeout,
            max_attempts=self.max_attempts,
            response_format=self.response_format,
        )
        return self.parse_response(raw)
