import json
import re

from app.agents.base import Agent, AnyNimClient
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default model — callers can override via subclass or direct instantiation
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class JdAnalyzerAgent(Agent):
    """Extracts structured requirements from a raw job description text."""

    name = "jd_analyzer"
    temperature = 0.1
    max_tokens = 2048

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You are a precise technical recruiter assistant that extracts structured information "
            "from job descriptions. Your output is consumed by a downstream resume tailoring "
            "pipeline, so accuracy and completeness of technical keywords matters more than "
            "interpretation.\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose, no explanation. "
            "Any text outside the JSON object will cause a parse error.\n\n"
            "Required JSON schema:\n"
            "{\n"
            '  "role_title": "string — exact job title as posted",\n'
            '  "company": "string — company name",\n'
            '  "experience_level": "string — one of: junior, mid, senior, staff, principal, manager",\n'
            '  "required_skills": ["must-have technical skills explicitly stated"],\n'
            '  "preferred_skills": ["nice-to-have skills or bonus qualifications"],\n'
            '  "key_responsibilities": ["3-6 specific responsibilities or expected outcomes"],\n'
            '  "themes": ["3-5 strategic themes, e.g. distributed systems, ml infrastructure"],\n'
            '  "domain": "primary domain, e.g. machine learning, backend engineering, data engineering",\n'
            '  "keywords": ["comprehensive list of all technical keywords, tools, frameworks, '
            'methodologies mentioned"],\n'
            '  "ats_critical": ["keywords most likely used by ATS filters, typically the '
            'first 5-10 emphasized in the job post"]\n'
            "}"
        )

    def user_prompt(self, jd_text: str, **_) -> str:
        return (
            "Extract structured requirements from this job description. "
            "Be exhaustive with keywords — include every tool, language, framework, "
            "methodology, and buzzword mentioned.\n\n"
            f"JOB DESCRIPTION:\n{jd_text}"
        )

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.JD_ANALYZER_FAILED,
                "The AI returned an unexpected response while analyzing the job description.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        required = {"role_title", "company", "required_skills", "keywords"}
        missing = required - data.keys()
        if missing:
            raise APIError(
                ErrorCode.JD_ANALYZER_FAILED,
                "The AI's job description analysis was incomplete.",
                technical_details=f"Missing fields: {missing}",
                retry_possible=True,
            )
        return data
