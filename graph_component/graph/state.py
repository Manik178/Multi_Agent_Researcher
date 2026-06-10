from typing import TypedDict, Annotated, Literal
import operator
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, field_validator


def replace_or_add(existing: list, new: list) -> list:
    if new == []:
        return []
    return existing + new

def sum_values(existing: int, new: int) -> int:
    return (existing or 0) + (new or 0)


class ResearchState(TypedDict):
    question: str
    sub_questions: list[str]
    document_context: str
    research_results: Annotated[list[dict], replace_or_add]
    critic_verdict: str
    critic_feedback: str
    critic_confidence: float
    verified_claims: list[dict]
    follow_up_questions: list[str]
    final_answer: str

    # These three get written by parallel nodes — need sum reducer
    cache_hits: Annotated[int, sum_values]
    qdrant_hits: Annotated[int, sum_values]
    total_sources: Annotated[int, sum_values]

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

class CitationVerifierOutput(BaseModel):
    verified_claims: list[dict]

    @field_validator("verified_claims", mode="before")
    @classmethod
    def validate_claims(cls, v):
        # Ensure each claim has required fields
        for item in v:
            if "claim" not in item:
                item["claim"] = ""
            if "verified" not in item:
                item["verified"] = False
            if "source_index" not in item:
                item["source_index"] = 0
        return v

class FollowUpOutput(BaseModel):
    follow_up_questions: list[str]

    @field_validator("follow_up_questions")
    @classmethod
    def validate_count(cls, v):
        return v[:3]  # cap at 3