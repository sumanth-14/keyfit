"""Unit tests for PipelineRunner._build_outreach_context.

The outreach agent used to receive only name + skills, which produced generic
messages. These tests pin the richer context payload it now receives.
"""

from app.models.pipeline import TailoredContent, TailoredExperience, TailoredProject
from app.models.profile import (
    Experience,
    PersonalInfo,
    Profile,
    Project,
)
from app.orchestration.pipeline_runner import PipelineRunner


def _profile() -> Profile:
    return Profile(
        personal=PersonalInfo(name="Sumanth", email="s@example.com"),
        summary="Original summary.",
        experience=[
            Experience(id="exp_1", title="ML Engineer", company="Acme", bullets=[]),
            Experience(id="exp_2", title="SWE Intern", company="Globex", bullets=[]),
        ],
        projects=[
            Project(
                id="proj_1",
                name="RAG Search",
                text="Built a retrieval system.",
                stack=["Python", "FAISS"],
                metrics=["40% faster"],
            ),
        ],
        skills={"Languages": ["Python", "Go"]},
    )


def _tailored() -> TailoredContent:
    return TailoredContent(
        summary="JD-tailored pitch about LLMs.",
        skills={"Languages": ["Python"]},
        experience=[
            TailoredExperience(
                role_id="exp_1",
                bullets=["Shipped an LLM pipeline cutting latency 30%.", "Led a team of 4."],
            ),
            TailoredExperience(
                role_id="exp_2", bullets=["Built internal tooling."]
            ),
        ],
        projects=[TailoredProject(project_id="proj_1")],
    )


def test_context_uses_tailored_summary_as_pitch():
    ctx = PipelineRunner._build_outreach_context(_profile(), _tailored())
    assert ctx["pitch"] == "JD-tailored pitch about LLMs."


def test_context_resolves_current_role_from_first_tailored_experience():
    ctx = PipelineRunner._build_outreach_context(_profile(), _tailored())
    assert ctx["current_role"] == "ML Engineer, Acme"


def test_context_pulls_top_achievements_from_tailored_bullets():
    ctx = PipelineRunner._build_outreach_context(_profile(), _tailored())
    # Up to 2 bullets from each of the first 2 roles, capped at 4.
    assert ctx["top_achievements"] == [
        "Shipped an LLM pipeline cutting latency 30%.",
        "Led a team of 4.",
        "Built internal tooling.",
    ]


def test_context_includes_standout_project_with_metrics():
    ctx = PipelineRunner._build_outreach_context(_profile(), _tailored())
    assert ctx["standout_project"] == {
        "name": "RAG Search",
        "what": "Built a retrieval system.",
        "stack": ["Python", "FAISS"],
        "metrics": ["40% faster"],
    }


def test_context_handles_empty_experience_and_projects():
    profile = Profile(personal=PersonalInfo(name="A", email="a@b.c"))
    tailored = TailoredContent(summary="x", skills={}, experience=[], projects=[])
    ctx = PipelineRunner._build_outreach_context(profile, tailored)
    assert ctx["current_role"] is None
    assert ctx["standout_project"] is None
    assert ctx["top_achievements"] == []
