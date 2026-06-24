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
    # A detailed resume's enriched JSON (themes/metrics/tech_stack per bullet)
    # can run long — keep generous headroom so the JSON is never truncated
    # mid-object (truncation -> invalid JSON -> parse failure). The small fast
    # model generates these tokens quickly, so this stays well under the budget.
    max_tokens = 4096
    # One shot with a generous 90s cap: free-tier generation of the full enriched
    # JSON can take well over 25s, and cutting it off mid-output produced the
    # unparseable responses we saw. Still bounded (no multi-minute retry ladder).
    request_timeout = 90.0
    max_attempts = 1
    # NOTE: response_format json_object was removed — it appears to cause an
    # immediate request rejection on some NIM models (e.g. qwen2.5-7b). Qwen2.5
    # adheres to JSON well on its own, and parse_response sanitizes stragglers.

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You extract structured profile data from resume text into JSON. Copy the "
            "content as written — do not invent, summarize, or embellish anything.\n\n"
            "ID rules:\n"
            "- Experience IDs: exp_1, exp_2, ... (newest job first, so exp_1 = most recent)\n"
            "- Bullet IDs: exp_1_b1, exp_1_b2, ... (per experience, top bullet first)\n"
            "- Project IDs: proj_1, proj_2, ...   Education IDs: edu_1, edu_2, ...\n"
            "- level: L4 = most recent job, then L3, L2, L1 = oldest.\n\n"
            "For visa_status.type use one of: citizen, green_card, h1b, opt, cpt, tn, other, "
            "unknown. If not mentioned, use 'unknown' and needs_sponsorship false.\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose, no trailing commas.\n\n"
            "Required JSON schema:\n"
            '{"personal": {"name": "str", "email": "str", "phone": "str|null", '
            '"location": "str|null", "linkedin": "str|null", "github": "str|null", '
            '"portfolio": "str|null"}, '
            '"visa_status": {"type": "str", "needs_sponsorship": bool}, '
            '"education": [{"id": "str", "degree": "str", "school": "str", "location": "str|null", '
            '"dates": "str|null", "gpa": "float|null"}], '
            '"experience": [{"id": "str", "title": "str", "company": "str", "location": "str|null", '
            '"dates": "str|null", "level": "L1|L2|L3|L4", '
            '"bullets": [{"id": "str", "text": "str"}]}], '
            '"projects": [{"id": "str", "name": "str", "subtitle": "str|null", '
            '"stack": ["str"], "text": "str", "url": "str|null"}], '
            '"skills": {"Category": ["skill1", "skill2"]}}'
        )

    def user_prompt(self, resume_text: str, **_) -> str:
        return (
            "Extract the professional profile from this resume text into the required JSON. "
            "Copy each bullet's wording accurately.\n\n"
            f"RESUME:\n{resume_text[:8000]}"
        )

    def parse_response(self, raw: str) -> dict:
        # Small models sometimes wrap the JSON in markdown fences or a sentence
        # of prose. Strip fences, then slice to the outermost { ... } so leading/
        # trailing chatter doesn't break json.loads.
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
        # Small models routinely emit trailing commas (e.g. `"x": 1,\n}`), which
        # are invalid JSON. Drop any comma that directly precedes a } or ].
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Log length + head + tail so production logs disambiguate truncation
            # (tail will be a dangling token) from a mid-output syntax error.
            logger.warning(
                f"resume_parser could not parse model output "
                f"len={len(raw)} head={raw[:300]!r} tail={raw[-300:]!r}"
            )
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
