import json
import re

from app.agents.base import Agent, AnyNimClient
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class OutreachAgent(Agent):
    """Generates cold outreach messages (email + LinkedIn) for a job application."""

    name = "outreach"
    temperature = 0.7
    max_tokens = 3000

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You write personalized, professional cold outreach messages for job applications. "
            "You sound like the candidate themselves — confident, specific, not desperate "
            "or generic. Every message must reference something specific about the role or "
            "company, and lead with the candidate's most relevant achievement.\n\n"
            "STRICT CHARACTER LIMITS:\n"
            "- linkedin_connection_note: max 200 characters (hard LinkedIn platform limit)\n"
            "- cold_email_body: 150-200 words\n"
            "- linkedin_inmail_body: 200-300 words\n\n"
            "Message style:\n"
            "- Open cold email with a specific observation about the company/role, "
            "NOT 'I saw your job posting on LinkedIn'\n"
            "- End cold email with one low-friction ask (e.g. '15-minute call', "
            "NOT 'I'd love to discuss opportunities')\n"
            "- LinkedIn connection note: conversational, human, no hard sell\n"
            "- LinkedIn InMail: more formal, closer to cold email tone, has a subject line\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose.\n\n"
            "Required JSON schema:\n"
            "{\n"
            '  "messages": {\n'
            '    "cold_email_subject": "compelling subject line, 6-10 words",\n'
            '    "cold_email_body": "professional cold email body, 150-200 words",\n'
            '    "linkedin_connection_note": "brief connection request, STRICT MAX 200 chars",\n'
            '    "linkedin_inmail_subject": "InMail subject line, 5-8 words",\n'
            '    "linkedin_inmail_body": "professional InMail, 200-300 words"\n'
            "  },\n"
            '  "personalization_used": ["specific details from JD/company used to personalize"]\n'
            "}"
        )

    def user_prompt(
        self,
        profile_summary: dict,
        jd_analysis: dict,
        company_name: str,
        role_title: str,
        contact_name: str | None = None,
        contact_type: str | None = None,
        **_,
    ) -> str:
        contact_line = ""
        if contact_name:
            contact_line = (
                f"Contact name: {contact_name}"
                + (f" ({contact_type})" if contact_type else "")
                + "\n"
            )

        return (
            f"COMPANY: {company_name}\n"
            f"ROLE: {role_title}\n"
            f"{contact_line}"
            f"DOMAIN: {jd_analysis.get('domain', 'software engineering')}\n"
            f"KEY THEMES: {', '.join(jd_analysis.get('themes', []))}\n"
            f"TOP JD KEYWORDS: {', '.join(jd_analysis.get('ats_critical', jd_analysis.get('keywords', []))[:10])}\n\n"
            f"CANDIDATE:\n{json.dumps(profile_summary, indent=2)}\n\n"
            "Write all five outreach messages. "
            "Personalize each one using specific details from the role and company above. "
            "Return JSON only."
        )

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.OUTREACH_FAILED,
                "The AI returned an unexpected response while generating outreach messages.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        if "messages" not in data:
            raise APIError(
                ErrorCode.OUTREACH_FAILED,
                "The AI's outreach output was incomplete.",
                technical_details="Missing messages field",
                retry_possible=True,
            )
        return data
