import json

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Hardcoded JSON responses keyed by the agent name passed as the first word
# of the system prompt. Each agent's parse_response() must be able to parse
# these — keep in sync when agents are updated.
_MOCK_RESPONSES: dict[str, str] = {
    "jd_analyzer": json.dumps({
        "role_title": "Software Engineer",
        "company": "ACME Corp",
        "required_skills": ["Python", "FastAPI", "Docker"],
        "preferred_skills": ["Kubernetes", "Redis"],
        "key_responsibilities": [
            "Build and maintain backend services",
            "Design RESTful APIs",
        ],
        "experience_level": "mid",
        "themes": ["backend", "cloud", "API"],
        "keywords": ["Python", "FastAPI", "Docker", "REST", "microservices"],
    }),
    "tailor": json.dumps({
        "summary": "Backend engineer with FastAPI and Docker experience.",
        "skills": {},
        "experience": [],
        "projects": [],
    }),
    "critic": json.dumps({
        "scores": {
            "ats_keyword_match": {"score": 20, "max": 25},
            "impact_metrics": {"score": 20, "max": 25},
            "bullet_quality": {"score": 16, "max": 20},
            "role_alignment": {"score": 12, "max": 15},
            "clarity": {"score": 12, "max": 15},
        },
        "total": 80,
        "verdict": "STRONG MATCH",
        "keywords_found": ["Python", "FastAPI", "Docker"],
        "keywords_missing": ["Kubernetes"],
        "top_fixes": [
            {"priority": "MEDIUM", "fix": "Add Kubernetes if you have experience with it"},
        ],
    }),
    "outreach": json.dumps({
        "messages": {
            "cold_email_subject": "Backend engineer drawn to ACME's API-first platform",
            "cold_email_body": (
                "Hi,\n\nI came across the Software Engineer opening at ACME Corp and "
                "was drawn to your API-first engineering culture. I've shipped "
                "production FastAPI services and would love to bring that to your team. "
                "Could we find 15 minutes for a quick call?\n\nBest,\nJohn"
            ),
            "linkedin_connection_note": (
                "Hi! Backend engineer with Python/FastAPI experience — would love to "
                "connect about the SWE role at ACME."
            ),
            "linkedin_inmail_subject": "SWE role at ACME — quick intro",
            "linkedin_inmail_body": (
                "Hi,\n\nI'm a backend engineer with Python/FastAPI experience and noticed "
                "the Software Engineer opening at ACME. I've built and scaled REST APIs "
                "and would welcome a short conversation about how I could contribute.\n\n"
                "Best,\nJohn"
            ),
        },
        "personalization_used": ["Referenced ACME's API-first engineering culture"],
    }),
    "resume_parser": json.dumps({
        "personal": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": None,
            "location": None,
            "linkedin": None,
            "github": None,
            "portfolio": None,
        },
        "visa_status": None,
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {},
        "extraction_confidence": {
            "personal": 0.9,
            "education": 0.0,
            "experience": 0.0,
            "projects": 0.0,
            "skills": 0.0,
        },
        "flagged_fields": [],
        "raw_extracted_text": "(mock parse — no real extraction performed)",
    }),
    "role_config_generator": json.dumps({
        "version": 1,
        "role_id": "generic_role",
        "role_display_name": "Generic Role",
        "source": "auto_generated",
        "generated_at": "2026-01-01T00:00:00Z",
        "skills_order": [
            "Programming Languages",
            "Frameworks & Libraries",
            "Databases & Storage",
            "Cloud & DevOps",
            "AI & ML",
            "Core Competencies",
        ],
        "bullet_priority_strategy": "Lead with most relevant technical bullets.",
        "project_priority_strategy": "Lead with most technically complex projects.",
        "summary_focus": "Technical depth and impact.",
        "keywords_emphasis": [],
        "preferred_action_verbs": ["Built", "Designed", "Implemented", "Led"],
        "bullets_per_role_max": {"R4": 3, "R3": 3, "R2": 2, "R1": 1},
    }),
}

_DEFAULT_RESPONSE = json.dumps({"result": "mock response — agent not recognized"})


class MockNimClient:
    """Drop-in replacement for NimClient that returns hardcoded JSON.

    Keyed by the agent's `name` (passed as `agent_name`). Falls back to the first
    word of the system prompt for any caller that doesn't set a name.
    Use when settings.use_mock_nim is True so dev/test cycles don't burn NIM credits.
    """

    async def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        agent_name: str = "",
        timeout: float | None = None,
        max_attempts: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        key = agent_name.lower() if agent_name else (system.split()[0].lower() if system else "")
        response = _MOCK_RESPONSES.get(key, _DEFAULT_RESPONSE)
        logger.info(f"MockNimClient returning canned response for key={key!r}")
        return response
