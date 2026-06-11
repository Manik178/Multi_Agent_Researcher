"""
RAGAS-style Evaluators for Multi-Agent Researcher
===================================================
Implements the industry-standard "Big Four" RAG evaluation metrics:
1. Faithfulness       — Is the answer grounded in the retrieved context?
2. Answer Relevance   — Does the answer address the user's question?
3. Context Precision  — Are the retrieved chunks actually useful?
4. Context Recall     — Did retrieval find everything needed?

Plus heuristic (non-LLM) evaluators that cost zero tokens:
5. Citation Coverage  — Does the answer contain proper citation markers?
6. Latency Tracking   — How long did the full graph take?
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os
import re
import time
from dotenv import load_dotenv

load_dotenv()

# ── Rate-limited evaluator LLM ─────────────────────────────────
# Using the small, fast model so evaluator calls stay under free-tier limits.
eval_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY")
)

# Helper to add a delay between LLM evaluator calls
def _rate_limit_pause():
    time.sleep(3)   # 3-second pause between evaluator LLM calls

# ── Shared helpers ──────────────────────────────────────────────

def _extract_context(outputs: dict) -> str:
    """Combine all research_results summaries into a single context string."""
    results = outputs.get("research_results", [])
    parts = []
    for r in results:
        if isinstance(r, dict):
            parts.append(r.get("summary", r.get("content", "")))
    return "\n\n".join(parts)


def _extract_sub_questions(outputs: dict) -> list[str]:
    return outputs.get("sub_questions", [])

# ══════════════════════════════════════════════════════════════════
#  RAGAS METRIC 1: Faithfulness (Hallucination Detection)
# ══════════════════════════════════════════════════════════════════

class FaithfulnessScore(BaseModel):
    score: float = Field(
        description="A score between 0.0 and 1.0. 1.0 means every claim is supported by context. 0.0 means none are.",
        ge=0.0, le=1.0
    )
    supported_claims: int = Field(description="Number of claims supported by the context")
    total_claims: int = Field(description="Total number of factual claims in the answer")
    reasoning: str = Field(description="Brief explanation")

faithfulness_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert fact-checker performing a Faithfulness evaluation.

TASK: Extract every factual claim from the Final Answer, then check each claim against the Context.

SCORING:
- Count the total number of distinct factual claims in the answer.
- Count how many of those claims are directly supported by the context.
- Score = supported_claims / total_claims (a float between 0.0 and 1.0).

Be strict: if a claim adds information NOT in the context, it is unsupported."""),
    ("user", """Context (retrieved research):
{context}

Final Answer to evaluate:
{answer}""")
])

faithfulness_chain = faithfulness_prompt | eval_llm.with_structured_output(FaithfulnessScore)

def faithfulness_evaluator(run: Any, example: Any) -> dict:
    outputs = run.outputs or {}
    final_answer = outputs.get("final_answer", "")
    context_text = _extract_context(outputs)

    if not final_answer:
        return {"key": "faithfulness", "score": 0.0, "comment": "No final answer generated."}
    if not context_text:
        return {"key": "faithfulness", "score": 0.0, "comment": "No research context to evaluate against."}

    try:
        _rate_limit_pause()
        result = faithfulness_chain.invoke({"context": context_text, "answer": final_answer})
        return {
            "key": "faithfulness",
            "score": result.score,
            "comment": f"{result.supported_claims}/{result.total_claims} claims supported. {result.reasoning}"
        }
    except Exception as e:
        return {"key": "faithfulness", "score": 0.0, "comment": f"Evaluator error: {e}"}


# ══════════════════════════════════════════════════════════════════
#  RAGAS METRIC 2: Answer Relevance
# ══════════════════════════════════════════════════════════════════

class RelevanceScore(BaseModel):
    score: float = Field(
        description="A score between 0.0 and 1.0. 1.0 means the answer fully addresses the question.",
        ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Brief explanation")

relevance_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert evaluator performing an Answer Relevance assessment.

TASK: Determine how well the Final Answer addresses the Original Question.

SCORING (float between 0.0 and 1.0):
- 1.0: The answer directly, completely, and concisely addresses every part of the question.
- 0.7-0.9: The answer addresses the question but is missing minor details or includes some irrelevant information.
- 0.4-0.6: The answer partially addresses the question but has significant gaps.
- 0.0-0.3: The answer fails to address the question or is mostly irrelevant."""),
    ("user", """Original Question:
{question}

Final Answer:
{answer}""")
])

relevance_chain = relevance_prompt | eval_llm.with_structured_output(RelevanceScore)

def answer_relevance_evaluator(run: Any, example: Any) -> dict:
    inputs = example.inputs or {}
    outputs = run.outputs or {}
    question = inputs.get("question", "")
    final_answer = outputs.get("final_answer", "")

    if not final_answer:
        return {"key": "answer_relevance", "score": 0.0, "comment": "No final answer generated."}

    try:
        _rate_limit_pause()
        result = relevance_chain.invoke({"question": question, "answer": final_answer})
        return {
            "key": "answer_relevance",
            "score": result.score,
            "comment": result.reasoning
        }
    except Exception as e:
        return {"key": "answer_relevance", "score": 0.0, "comment": f"Evaluator error: {e}"}


# ══════════════════════════════════════════════════════════════════
#  RAGAS METRIC 3: Context Precision
# ══════════════════════════════════════════════════════════════════

class ContextPrecisionScore(BaseModel):
    score: float = Field(
        description="A score between 0.0 and 1.0. 1.0 means all retrieved chunks were relevant.",
        ge=0.0, le=1.0
    )
    relevant_chunks: int = Field(description="Number of retrieved chunks that are relevant to the question")
    total_chunks: int = Field(description="Total number of retrieved chunks")
    reasoning: str = Field(description="Brief explanation")

context_precision_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert evaluator performing a Context Precision assessment.

TASK: Evaluate whether the retrieved context chunks are relevant to answering the question.

You will receive the original question and all the retrieved research chunks.
For each chunk, determine if it contains information useful for answering the question.

SCORING:
- Count total chunks and how many are relevant.
- Score = relevant_chunks / total_chunks (a float between 0.0 and 1.0).
- If all chunks are relevant, score is 1.0 (perfect precision)."""),
    ("user", """Original Question:
{question}

Retrieved Context Chunks:
{context}""")
])

context_precision_chain = context_precision_prompt | eval_llm.with_structured_output(ContextPrecisionScore)

def context_precision_evaluator(run: Any, example: Any) -> dict:
    inputs = example.inputs or {}
    outputs = run.outputs or {}
    question = inputs.get("question", "")
    results = outputs.get("research_results", [])

    if not results:
        return {"key": "context_precision", "score": 0.0, "comment": "No context retrieved."}

    # Format each chunk separately so the judge can evaluate them individually
    chunks_text = "\n\n".join([
        f"--- Chunk {i+1} ---\nSub-question: {r.get('question', 'N/A')}\nContent: {r.get('summary', r.get('content', ''))}"
        for i, r in enumerate(results) if isinstance(r, dict)
    ])

    try:
        _rate_limit_pause()
        result = context_precision_chain.invoke({"question": question, "context": chunks_text})
        return {
            "key": "context_precision",
            "score": result.score,
            "comment": f"{result.relevant_chunks}/{result.total_chunks} chunks relevant. {result.reasoning}"
        }
    except Exception as e:
        return {"key": "context_precision", "score": 0.0, "comment": f"Evaluator error: {e}"}


# ══════════════════════════════════════════════════════════════════
#  RAGAS METRIC 4: Context Recall
# ══════════════════════════════════════════════════════════════════

class ContextRecallScore(BaseModel):
    score: float = Field(
        description="A score between 0.0 and 1.0. 1.0 means the context contains everything needed.",
        ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Brief explanation of what was found or missing")

context_recall_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert evaluator performing a Context Recall assessment.

TASK: Given the original question and the retrieved context, determine if the context
contains ALL the information needed to fully answer the question.

SCORING (float between 0.0 and 1.0):
- 1.0: The context contains all facts, data, and details needed for a complete answer.
- 0.7-0.9: The context covers most aspects but is missing minor details.
- 0.4-0.6: The context covers some aspects but has significant gaps.
- 0.0-0.3: The context is mostly insufficient to answer the question."""),
    ("user", """Original Question:
{question}

Retrieved Context:
{context}""")
])

context_recall_chain = context_recall_prompt | eval_llm.with_structured_output(ContextRecallScore)

def context_recall_evaluator(run: Any, example: Any) -> dict:
    inputs = example.inputs or {}
    outputs = run.outputs or {}
    question = inputs.get("question", "")
    context_text = _extract_context(outputs)

    if not context_text:
        return {"key": "context_recall", "score": 0.0, "comment": "No context retrieved."}

    try:
        _rate_limit_pause()
        result = context_recall_chain.invoke({"question": question, "context": context_text})
        return {
            "key": "context_recall",
            "score": result.score,
            "comment": result.reasoning
        }
    except Exception as e:
        return {"key": "context_recall", "score": 0.0, "comment": f"Evaluator error: {e}"}


# ══════════════════════════════════════════════════════════════════
#  HEURISTIC METRIC 5: Citation Coverage (Zero LLM cost)
# ══════════════════════════════════════════════════════════════════

def citation_coverage_evaluator(run: Any, example: Any) -> dict:
    """Checks if the system's citation verifier found and verified claims."""
    outputs = run.outputs or {}
    verified_claims = outputs.get("verified_claims", [])

    if not verified_claims:
        return {"key": "citation_coverage", "score": 0.0, "comment": "No verified claims found in output."}

    total = len(verified_claims)
    verified = sum(1 for c in verified_claims if c.get("verified", False))
    score = verified / total if total > 0 else 0.0

    return {
        "key": "citation_coverage",
        "score": round(score, 2),
        "comment": f"{verified}/{total} claims verified by citation verifier."
    }


# ══════════════════════════════════════════════════════════════════
#  HEURISTIC METRIC 6: Answer Completeness (Zero LLM cost)
# ══════════════════════════════════════════════════════════════════

def answer_completeness_evaluator(run: Any, example: Any) -> dict:
    """Checks structural quality of the answer: length, headings, sub-question coverage."""
    outputs = run.outputs or {}
    final_answer = outputs.get("final_answer", "")
    sub_questions = outputs.get("sub_questions", [])

    if not final_answer:
        return {"key": "answer_completeness", "score": 0.0, "comment": "No answer generated."}

    score = 0.0
    comments = []

    # Check minimum length (a good answer should be at least 200 chars)
    if len(final_answer) >= 500:
        score += 0.4
        comments.append("Good length (500+ chars)")
    elif len(final_answer) >= 200:
        score += 0.2
        comments.append("Acceptable length (200+ chars)")
    else:
        comments.append(f"Short answer ({len(final_answer)} chars)")

    # Check if answer contains markdown structure (headers, bullets, bold)
    has_structure = bool(re.search(r'(#{1,3}\s|[-*]\s|\*\*)', final_answer))
    if has_structure:
        score += 0.3
        comments.append("Has markdown structure")
    else:
        comments.append("No markdown formatting")

    # Check if follow-up questions were generated
    follow_ups = outputs.get("follow_up_questions", [])
    if len(follow_ups) >= 3:
        score += 0.3
        comments.append(f"{len(follow_ups)} follow-up questions generated")
    elif follow_ups:
        score += 0.15
        comments.append(f"Only {len(follow_ups)} follow-ups (expected 3)")

    return {
        "key": "answer_completeness",
        "score": round(min(score, 1.0), 2),
        "comment": "; ".join(comments)
    }


# ══════════════════════════════════════════════════════════════════
#  HEURISTIC METRIC 7: Retrieval Efficiency (Zero LLM cost)
# ══════════════════════════════════════════════════════════════════

def retrieval_efficiency_evaluator(run: Any, example: Any) -> dict:
    """Measures cache hit ratio — higher = more efficient (fewer API calls)."""
    outputs = run.outputs or {}

    cache_hits = outputs.get("cache_hits", 0)
    qdrant_hits = outputs.get("qdrant_hits", 0)
    web_searches = outputs.get("total_sources", 0)
    total = cache_hits + qdrant_hits + web_searches

    if total == 0:
        return {"key": "retrieval_efficiency", "score": 0.0, "comment": "No retrievals recorded."}

    # Cache & qdrant hits are "free" — web searches cost money and time
    efficiency = (cache_hits + qdrant_hits) / total
    return {
        "key": "retrieval_efficiency",
        "score": round(efficiency, 2),
        "comment": f"Cache: {cache_hits}, Qdrant: {qdrant_hits}, Web: {web_searches} (total: {total})"
    }
