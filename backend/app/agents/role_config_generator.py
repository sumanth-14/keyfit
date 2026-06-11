import json
import re
from datetime import datetime, timezone

from app.agents.base import Agent, AnyNimClient
from app.models.errors import APIError, ErrorCode
from app.models.role_config import RoleConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class RoleConfigGeneratorAgent(Agent):
    """Generates a RoleConfig JSON for an unknown role title (Rule 6)."""

    name = "role_config_generator"
    temperature = 0.2
    max_tokens = 2048

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You generate resume tailoring strategy configurations for specific job roles. "
            "These configs guide how a candidate's resume should be customized for a "
            "particular role type — which skills to surface first, which bullet types "
            "to prioritize, and which keywords an ATS would scan for.\n\n"
            "EXAMPLE CONFIG (for reference):\n"
            '{"role_id": "software_engineer", "role_display_name": "Software Engineer", '
            '"skills_order": ["Languages", "Frameworks", "Cloud & Infrastructure", "Databases"], '
            '"bullet_priority_strategy": "Prioritize system design, scalability, and full-stack '
            'ownership bullets. Lead with backend impact metrics and architectural decisions.", '
            '"project_priority_strategy": "Select projects showing end-to-end ownership, '
            'technical depth, and real-world user or business impact.", '
            '"summary_focus": "Versatile engineer with full-stack depth and strong system '
            'design background, experienced shipping production services at scale.", '
            '"keywords_emphasis": ["distributed systems", "microservices", "REST APIs", '
            '"CI/CD", "system design", "agile", "code review", "testing"], '
            '"preferred_action_verbs": ["Architected", "Engineered", "Optimized", "Scaled", '
            '"Deployed", "Led", "Reduced", "Shipped"], '
            '"bullets_per_role_max": {"L4": 4, "L3": 3, "L2": 2, "L1": 1}}\n\n'
            "Output ONLY valid JSON — no markdown fences, no prose.\n\n"
            "Required JSON schema:\n"
            '{"role_id": "snake_case — must match the requested role_id exactly", '
            '"role_display_name": "human-readable title", '
            '"skills_order": ["skill category names most relevant to this role, most important first"], '
            '"bullet_priority_strategy": "which types of experience bullets to prioritize", '
            '"project_priority_strategy": "which types of projects to select", '
            '"summary_focus": "1-sentence ideal candidate positioning for this role", '
            '"keywords_emphasis": ["8-12 domain-specific keywords an ATS would scan for"], '
            '"preferred_action_verbs": ["6-8 strong action verbs preferred for this role"], '
            '"bullets_per_role_max": {"L4": 4, "L3": 3, "L2": 2, "L1": 1}}'
        )

    def user_prompt(self, role_id: str, **_) -> str:
        display_name = role_id.replace("_", " ").title()
        return (
            f"Generate a resume tailoring configuration for the role: {display_name}\n"
            f"The role_id field must be exactly: {role_id}\n\n"
            "Think about what makes a strong candidate for this role — what skills should "
            "appear first, which achievements are most impressive to hiring managers in this "
            "domain, and which keywords ATS systems at top tech companies use for this role.\n\n"
            "Return JSON only."
        )

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "The AI returned an unexpected response while generating role configuration.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        if "role_id" not in data:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "The AI's role config output was incomplete.",
                technical_details="Missing role_id",
                retry_possible=True,
            )
        return data

    async def run_and_build(self, role_id: str) -> RoleConfig:
        """Run the agent and return a validated RoleConfig model."""
        data = await self.run(role_id=role_id)
        data["version"] = 1
        data["source"] = "auto_generated"
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        return RoleConfig.model_validate(data)
