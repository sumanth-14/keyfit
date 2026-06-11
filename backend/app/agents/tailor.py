import json
import re

from app.agents.base import Agent, AnyNimClient
from app.models.errors import APIError, ErrorCode
from app.models.pipeline import TailoredContent
from app.models.profile import Profile
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class TailorAgent(Agent):
    """Reorders and lightly rewords the user's profile to match a job description.

    Preservation guarantee (Rule 5): every experience entry, every bullet, and
    every project from the profile appears in the output.  The agent rewords
    bullets to surface JD keywords but must never invent metrics, drop entries,
    or fabricate experience.
    """

    name = "tailor"
    temperature = 0.3
    max_tokens = 4096

    def __init__(self, nim_client: AnyNimClient, model: str = DEFAULT_MODEL) -> None:
        super().__init__(nim_client, model)

    def system_prompt(self) -> str:
        return (
            "You are a professional resume tailoring assistant. Your job is to tailor "
            "a candidate's existing resume content to match a specific job description.\n\n"
            "YOUR ROLE IS TO PRESERVE AND REORDER — NOT TO SELECT A SUBSET.\n\n"
            "ABSOLUTE RULES:\n"
            "1. OUTPUT EVERY experience entry from the profile — do not drop any role.\n"
            "2. OUTPUT EVERY bullet for each experience entry — same count as input.\n"
            "3. OUTPUT EVERY project from the profile — do not drop any project.\n"
            "4. You MAY lightly reword bullets to naturally include JD keywords, but you "
            "MUST preserve every metric (%, numbers, $), every award name, and every "
            "specific technology mentioned in the original bullet.\n"
            "5. You MUST NOT invent new bullets, fabricate metrics, or add experience "
            "that does not exist in the profile.\n"
            "6. Reorder experience entries and projects by JD relevance if appropriate, "
            "but most-recent role should generally stay first.\n"
            "7. For skills: include ALL skills from the profile, reorder within each "
            "category to put JD-relevant skills first.\n"
            "8. Generate a 2–3 sentence summary tailored to this specific role. If the "
            "profile has a summary field, use it as a starting point.\n\n"
            "Output ONLY valid JSON — no markdown fences, no prose, no explanation."
        )

    def user_prompt(
        self,
        profile: "Profile",
        jd_analysis: dict,
        role_config: dict,
        prev_critique: dict | None = None,
        validation_error: str | None = None,
        **_,
    ) -> str:
        profile_data = {
            "summary": profile.summary,
            "experience": [
                {
                    "id": exp.id,
                    "title": exp.title,
                    "company": exp.company,
                    "bullets": [{"id": b.id, "text": b.text} for b in exp.bullets],
                }
                for exp in profile.experience
            ],
            "projects": [
                {"id": p.id, "name": p.name, "themes": p.themes, "stack": p.stack}
                for p in profile.projects
            ],
            "skills": profile.skills,
        }

        exp_counts = ", ".join(
            f"{exp.id}: {len(exp.bullets)} bullets" for exp in profile.experience
        )

        prompt = (
            "JOB DESCRIPTION ANALYSIS:\n"
            f"{json.dumps(jd_analysis, indent=2)}\n\n"
            "ROLE CONFIG (tailoring strategy):\n"
            f"{json.dumps(role_config, indent=2)}\n\n"
            "USER PROFILE:\n"
            f"{json.dumps(profile_data, indent=2)}\n\n"
            "PRESERVATION REQUIREMENTS (violations cause a hard retry):\n"
            f"- experience must contain exactly these role IDs: "
            f"{[exp.id for exp in profile.experience]}\n"
            f"- bullet counts per role must be: {exp_counts}\n"
            f"- projects must contain exactly these IDs: {[p.id for p in profile.projects]}\n\n"
            "TASK:\n"
            "Produce tailored resume content. Output ONLY valid JSON matching this schema:\n\n"
            "{\n"
            '  "summary": "2-3 sentence summary tailored to this specific role and JD",\n'
            '  "skills": {\n'
            '    "Category Name": ["skill1", "skill2", ...],\n'
            '    ... (ALL skill categories from profile, ordered by JD relevance)\n'
            "  },\n"
            '  "experience": [\n'
            '    {\n'
            '      "role_id": "exp_id_from_profile",\n'
            '      "bullets": [\n'
            '        "reworded or original bullet text",\n'
            '        ... (SAME NUMBER of bullets as in profile for this role)\n'
            '      ]\n'
            '    },\n'
            "    ... (ONE entry per experience entry in profile, no more, no less)\n"
            "  ],\n"
            '  "projects": [\n'
            '    {"project_id": "proj_id_from_profile"},\n'
            "    ... (ALL projects from profile, reordered by JD relevance)\n"
            "  ]\n"
            "}"
        )

        if prev_critique:
            prompt += (
                "\n\nPREVIOUS CRITIQUE (incorporate feedback only where the profile "
                "genuinely supports it — do NOT fabricate):\n"
                f"{json.dumps(prev_critique, indent=2)}"
            )

        if validation_error:
            prompt += (
                "\n\n⚠️  VALIDATION FAILED ON LAST ATTEMPT — YOU MUST FIX THIS:\n"
                f"{validation_error}\n"
                "Carefully re-read the PRESERVATION REQUIREMENTS above. "
                "Every role ID must appear. Every project ID must appear. "
                "Bullet counts must match exactly. Do not drop anything."
            )

        return prompt

    def parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise APIError(
                ErrorCode.TAILOR_FAILED,
                "The AI returned an unexpected response while tailoring your resume.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

        for key in ("summary", "skills", "experience", "projects"):
            if key not in data:
                raise APIError(
                    ErrorCode.TAILOR_FAILED,
                    "The AI's tailoring output was missing required fields.",
                    technical_details=f"Missing key: {key!r}",
                    retry_possible=True,
                )

        if not isinstance(data["experience"], list):
            raise APIError(
                ErrorCode.TAILOR_FAILED,
                "The AI returned malformed tailoring output.",
                technical_details="'experience' must be a list",
                retry_possible=True,
            )
        if not isinstance(data["projects"], list):
            raise APIError(
                ErrorCode.TAILOR_FAILED,
                "The AI returned malformed tailoring output.",
                technical_details="'projects' must be a list",
                retry_possible=True,
            )

        return data

    def validate_tailored_output(
        self, content: TailoredContent, profile: "Profile"
    ) -> None:
        """Enforce Rule 5 preservation: all roles, all bullets, all projects must be present."""
        violations: list[str] = []

        profile_role_ids = [exp.id for exp in profile.experience]
        profile_role_map = {exp.id: exp for exp in profile.experience}
        tailored_role_ids = [te.role_id for te in content.experience]

        # Check all profile roles are present
        missing_roles = set(profile_role_ids) - set(tailored_role_ids)
        if missing_roles:
            violations.append(f"Missing role IDs: {sorted(missing_roles)}")

        # Check no phantom roles were invented
        phantom_roles = set(tailored_role_ids) - set(profile_role_ids)
        if phantom_roles:
            violations.append(f"Invented role IDs not in profile: {sorted(phantom_roles)}")

        # Check bullet counts match for each role
        for te in content.experience:
            if te.role_id not in profile_role_map:
                continue  # already flagged above
            expected = len(profile_role_map[te.role_id].bullets)
            got = len(te.bullets)
            if got != expected:
                violations.append(
                    f"Role {te.role_id!r}: expected {expected} bullets, got {got}"
                )

        # Check all profile projects are present
        profile_proj_ids = {p.id for p in profile.projects}
        tailored_proj_ids = {tp.project_id for tp in content.projects}

        missing_projs = profile_proj_ids - tailored_proj_ids
        if missing_projs:
            violations.append(f"Missing project IDs: {sorted(missing_projs)}")

        phantom_projs = tailored_proj_ids - profile_proj_ids
        if phantom_projs:
            violations.append(f"Invented project IDs not in profile: {sorted(phantom_projs)}")

        if violations:
            raise APIError(
                ErrorCode.TAILOR_VALIDATION_FAILED,
                "The AI dropped content from your resume. Retrying with stricter instructions.",
                technical_details="; ".join(violations),
                retry_possible=True,
            )
