from pydantic import BaseModel, Field


class CritiqueScore(BaseModel):
    score: int
    max: int


class TopFix(BaseModel):
    priority: str  # "HIGH" | "MEDIUM" | "LOW"
    fix: str


class Critique(BaseModel):
    version: int = 1
    scores: dict[str, CritiqueScore] = Field(default_factory=dict)
    total: int
    verdict: str  # "STRONG MATCH" | "NEEDS WORK" | "WEAK MATCH"
    keywords_found: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)
    top_fixes: list[TopFix] = Field(default_factory=list)

    @staticmethod
    def color_for_score(score: int) -> str:
        if score >= 80:
            return "green"
        if score >= 60:
            return "yellow"
        return "red"

    @staticmethod
    def verdict_for_score(score: int) -> str:
        if score >= 80:
            return "STRONG MATCH"
        if score >= 60:
            return "NEEDS WORK"
        return "WEAK MATCH"
