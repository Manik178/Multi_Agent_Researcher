from typing import TypedDict, Annotated
import operator
from pydantic import BaseModel

def replace_or_add(existing: list, new: list) -> list:
    # If new list is empty, it's a reset signal — clear everything
    if new == []:
        return []
    return existing + new

class ResearchState(TypedDict):
    question: str
    sub_questions: list[str]
    research_results: Annotated[list[dict], operator.add]
    critic_verdict: str
    critic_feedback: str
    final_answer: str
    iteration: int

class PlannerOutput(BaseModel):
    sub_questions: list[str]

class CriticOutput(BaseModel):
    verdict: str
    feedback: str