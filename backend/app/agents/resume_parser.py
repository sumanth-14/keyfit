import json
import re

from app.agents.base import Agent, AnyNimClient
from app.config import settings
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Small fast model by default (config-overridable) — parsing must answer inside
# the 30s UX budget, and extraction is mechanical enough not to need a 70B model.
DEFAULT_MODEL = settings.nim_parser_model


class ResumeParserAgent(Agent):
    """Extracts a structured Profile from raw resume text."""

    name = "resume_parser"
    temperature = 0.1
    max_tokens = 2048
    # Fail fast: one shot, ~25s cap. Better a quick "try again" than a 4-minute
    # hang walking the default 4-attempt / 120s-per-attempt retry ladder.
    request_timeout = 25.0
    max_attempts = 1

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You extract structured professional profile data from resume text and produce "
            "accurate, well-structured JSON that exactly matches the required schema.\n\n"
            "ID generation rules:\n"
            "- Experience IDs: exp_1, exp_2, ... (list newest job first, so exp_1 = most recent)\n"
            "- Bullet IDs: exp_1_b1, exp_1_b2, ... (per experience, first bullet = top bullet)\n"
            "- Project IDs: proj_1, proj_2, ...\n"
            "- Education IDs: edu_1, edu_2, ...\n\n"
            "For each bullet, extract:\n"
            "- themes: 2-4 thematic tags (e.g. 'distributed systems', 'cost reduction', 'ml training')\n"
            "- metrics: any quantified results (e.g. '40% latency reduction', '$2M ARR impact')\n"
            "- tech_stack: specific tools/technologies mentioned in or implied by the bullet\n\n"
            "Experience level (level field):\n"
            "- L4 = most recent job, L3 = second most recent, L2, L1 = oldest\n\n"
            "For visa_status.type use: citizen, green_card, h1b, opt, cpt, tn, other, or unknown\n"
            "If visa status is not mentioned, set type to 'unknown' and needs_sponsorship to false.\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose.\n\n"
            "Required JSON schema:\n"
            '{"personal": {"name": "str", "email": "str", "phone": "str|null", '
            '"location": "str|null", "linkedin": "str|null", "github": "str|null", '
            '"portfolio": "str|null"}, '
            '"visa_status": {"type": "str", "needs_sponsorship": bool, "stem_extension_eligible": bool}, '
            '"education": [{"id": "str", "degree": "str", "school": "str", "location": "str|null", '
            '"dates": "str|null", "gpa": "float|null"}], '
            '"experience": [{"id": "str", "title": "str", "company": "str", "location": "str|null", '
            '"dates": "str|null", "level": "L1|L2|L3|L4", '
            '"bullets": [{"id": "str", "text": "str", "themes": ["str"], '
            '"metrics": ["str"], "tech_stack": ["str"]}]}], '
            '"projects": [{"id": "str", "name": "str", "subtitle": "str|null", '
            '"stack": ["str"], "themes": ["str"], "text": "str", "metrics": ["str"], '
            '"url": "str|null"}], '
            '"skills": {"Category": ["skill1", "skill2"]}, '
            '"extraction_confidence": {"personal": 0.0-1.0, "education": 0.0-1.0, '
            '"experience": 0.0-1.0, "projects": 0.0-1.0, "skills": 0.0-1.0}, '
            '"flagged_fields": [{"path": "str", "reason": "str"}]}'
        )

    def user_prompt(self, resume_text: str, **_) -> str:
        return (
            "Extract the complete professional profile from this resume. "
            "Be thorough with bullet enrichment — populate themes, metrics, and tech_stack "
            "for every bullet. Flag any fields that were guessed or unclear.\n\n"
            f"RESUME:\n{resume_text[:8000]}"
        )

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "The AI returned an unexpected response while parsing your resume.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        if "personal" not in data:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "The AI's resume parsing output was incomplete.",
                technical_details="Missing 'personal' field",
                retry_possible=True,
            )
        return data
