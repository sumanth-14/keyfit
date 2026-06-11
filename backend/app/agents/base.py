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
        )
        return self.parse_response(raw)
