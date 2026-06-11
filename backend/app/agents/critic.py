import json
import re

from app.agents.base import Agent, AnyNimClient
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class CriticAgent(Agent):
    """Scores a tailored resume against a job description (0–100) and identifies gaps."""

    name = "critic"
    temperature = 0.1
    max_tokens = 2048

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You are a rigorous resume reviewer who evaluates how well a candidate's resume "
            "matches a specific job description. You think like both an ATS system and a "
            "senior hiring manager.\n\n"
            "Score on 5 dimensions (total = 100):\n"
            "- ats_keyword_match (max 25): Are the JD's required_skills and ats_critical keywords "
            "present verbatim or as close synonyms in the resume?\n"
            "- impact_metrics (max 25): Do bullets include quantified outcomes — %, $, user scale, "
            "throughput, latency improvements?\n"
            "- bullet_quality (max 20): Are bullets action-verb led, specific, achievement-oriented "
            "(not task lists)? Do they show ownership and scope?\n"
            "- role_alignment (max 15): Does the candidate's experience level, company prestige, "
            "and responsibilities plausibly match this role?\n"
            "- clarity (max 15): Is the resume scannable, well-structured, free of jargon overload "
            "and dense paragraphs?\n\n"
            "Verdict rules (based on total):\n"
            "- 80-100: STRONG MATCH\n"
            "- 60-79: NEEDS WORK\n"
            "- 0-59: WEAK MATCH\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose.\n\n"
            "Required JSON schema:\n"
            "{\n"
            '  "scores": {\n'
            '    "ats_keyword_match": {"score": int, "max": 25, "note": "brief reason"},\n'
            '    "impact_metrics": {"score": int, "max": 25, "note": "brief reason"},\n'
            '    "bullet_quality": {"score": int, "max": 20, "note": "brief reason"},\n'
            '    "role_alignment": {"score": int, "max": 15, "note": "brief reason"},\n'
            '    "clarity": {"score": int, "max": 15, "note": "brief reason"}\n'
            "  },\n"
            '  "total": int,\n'
            '  "verdict": "STRONG MATCH" or "NEEDS WORK" or "WEAK MATCH",\n'
            '  "keywords_found": ["JD keywords that appear in the resume"],\n'
            '  "keywords_missing": ["important JD keywords absent from the resume"],\n'
            '  "top_fixes": [\n'
            '    {"priority": "high" or "medium" or "low", "fix": "specific actionable suggestion"}\n'
            "  ]\n"
            "}\n\n"
            "top_fixes: 3-5 items, most impactful first. Name exact missing keywords or "
            "specific bullet improvements — never generic advice like 'add more metrics'."
        )

    def user_prompt(self, latex_source: str, jd_analysis: dict, **_) -> str:
        return (
            "Evaluate this resume against the job requirements. "
            "Score objectively — be strict on keyword matching, generous on intent.\n\n"
            f"JD REQUIREMENTS:\n{json.dumps(jd_analysis, indent=2)}\n\n"
            "RESUME (LaTeX source — evaluate the text content, ignore formatting commands):\n"
            f"{latex_source[:6000]}\n\n"
            "Return JSON only."
        )

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.CRITIC_FAILED,
                "The AI returned an unexpected response while critiquing your resume.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        required = {"scores", "total", "verdict", "keywords_found", "keywords_missing"}
        missing = required - data.keys()
        if missing:
            raise APIError(
                ErrorCode.CRITIC_FAILED,
                "The AI's critique was incomplete.",
                technical_details=f"Missing fields: {missing}",
                retry_possible=True,
            )
        return data
