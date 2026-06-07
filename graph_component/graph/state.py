from typing import TypedDict, Annotated, Literal
import operator
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, field_validator


def replace_or_add(existing: list, new: list) -> list:
    if new == []:
        return []
    return existing + new


class ResearchState(TypedDict):
    # Input
    question: str

    # H — Intent classification
    intent: str           # "factual" | "comparative" | "advisory" | "exploratory"
    search_depth: int     # 3 for factual, 5 for comparative/exploratory

    # Planner output
    sub_questions: list[str]

    # E — Document context (from uploaded docs)
    document_context: str  # concatenated relevant chunks from Qdrant private docs

    # Researcher output
    research_results: Annotated[list[dict], replace_or_add]

    # Critic output
    critic_verdict: str
    critic_feedback: str
    critic_confidence: float   # C — confidence score

    # G — Citation verification
    verified_claims: list[dict]    # {"claim": str, "verified": bool, "source": str}

    # B — Follow-up suggestions
    follow_up_questions: list[str]

    # Writer output
    final_answer: str

    # C — Confidence metadata
    cache_hits: int
    qdrant_hits: int
    total_sources: int
    iterations_needed: int

    # Control
    iteration: int
    approved: bool


# ── Pydantic models ───────────────────────────────────────────

class PlannerOutput(BaseModel):
    sub_questions: list[str]

from pydantic import BaseModel, Field, field_validator

class CriticOutput(BaseModel):
    verdict: str
    feedback: str
    confidence: float = Field(
        description="Confidence score as a decimal number between 0.0 and 1.0. Example: 0.9",
        ge=0.0,
        le=1.0
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, v):
        return float(v)

class IntentOutput(BaseModel):
    intent: Literal["factual", "comparative", "advisory", "exploratory"]
    search_depth: int
    reasoning: str

class CitationOutput(BaseModel):
    verified_claims: list[dict]

class FollowUpOutput(BaseModel):
    follow_up_questions: list[str]