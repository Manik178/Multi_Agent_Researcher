from pydantic import BaseModel

class ResearchRequest(BaseModel):
    question: str

class ResearchResponse(BaseModel):
    question: str
    sub_questions: list[str]
    iterations: int
    critic_verdict: str
    final_answer: str