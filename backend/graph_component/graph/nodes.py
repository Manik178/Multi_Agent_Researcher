import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from cache import get_cached, set_cached
from vector_store import search_similar, store_result
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from langchain_tavily import TavilySearch
from .state import ResearchState, PlannerOutput, CriticOutput, CitationVerifierOutput, FollowUpOutput
# pyrefly: ignore [missing-import]
from vector_store import search_similar, store_result, search_private_docs
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()
# pyrefly: ignore [missing-import]
from langchain_core.rate_limiters import InMemoryRateLimiter
import os

os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING", "false")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "multi-agent-researcher")


rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.2,   # 1 request every 2 seconds
    check_every_n_seconds=0.1,
    max_bucket_size=3
)

primary_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    rate_limiter=rate_limiter
)

fallback_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    rate_limiter=rate_limiter
)

llm = primary_llm.with_fallbacks([fallback_llm])
search_tool = TavilySearch(max_results=3)
# ── Node 1: Planner ──────────────────────────────────────────
def planner_node(state: ResearchState) -> dict:
    structured_llm = llm.with_structured_output(PlannerOutput)

    # Build system message
    system_msg = (
        "You are a research planner. Break the user's question into "
        "exactly 3 focused sub-questions that together would fully answer it. "
        "Each sub-question should be independently researchable."
    )

    # If this is a retry, inject critic feedback
    user_content = f"Question: {state['question']}"
    if state.get("critic_feedback"):
        user_content += (
            f"\n\nPrevious research was insufficient. Critic feedback:\n"
            f"{state['critic_feedback']}\n\n"
            f"Generate 3 NEW sub-questions that address these gaps specifically."
        )

    result = structured_llm.invoke([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content}
    ])

    return {
        "sub_questions": result.sub_questions,
        "iteration": state.get("iteration", 0),
        "research_results": []   # clear previous results on retry
    }

# ── Node 2: Researcher ───────────────────────────────────────
# This node runs once PER sub-question, in parallel
def researcher_node(state: ResearchState) -> dict:
    question = state["sub_questions"][0]

    # ── Tier 1: Redis exact cache ─────────────────────────────
    cached = get_cached(question)
    if cached:
        print(f"[CACHE HIT] {question[:60]}...")
        return {
            "research_results": [cached],
            "cache_hits": 1
        }

    # ── Tier 2: Private documents ─────────────────────────────
    doc_chunks = search_private_docs(question)
    if doc_chunks:
        # Synthesize chunks into a summary
        combined = "\n\n".join([
            f"[From {c['source']} p.{c['page']}]: {c['text']}"
            for c in doc_chunks
        ])
        summary = llm.invoke([
            {
                "role": "system",
                "content": (
                    "You are a research analyst. Summarize the provided document excerpts "
                    "into a concise, factual paragraph relevant to the question. "
                    "Always mention the source document name."
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nDocument excerpts:\n{combined}"
            }
        ])
        result = {
            "question": question,
            "summary": summary.content,
            "source": "private_documents",
            "chunks": [c["source"] for c in doc_chunks]
        }
        set_cached(question, result)
        return {
            "research_results": [result],
            "qdrant_hits": 1
        }

    # ── Tier 3: Qdrant web cache ──────────────────────────────
    similar = search_similar(question)
    if similar:
        set_cached(question, similar)
        return {
            "research_results": [similar],
            "qdrant_hits": 1
        }

    # ── Tier 4: Tavily web search ─────────────────────────────
    print(f"[FULL RESEARCH] {question[:60]}...")
    search_results = search_tool.invoke(question)

    summary = llm.invoke([
        {
            "role": "system",
            "content": (
                "You are a research analyst. Summarize the search results "
                "into a concise, factual paragraph relevant to the question. "
                "Cite key facts only."
            )
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nSearch Results: {search_results}"
        }
    ])

    result = {
        "question": question,
        "summary": summary.content,
        "source": "web",
        "chunks": []
    }

    set_cached(question, result)
    store_result(question, result)

    return {
        "research_results": [result],
        "total_sources": 1
    }

# ── Node 3: Critic ───────────────────────────────────────────
def critic_node(state: ResearchState) -> dict:
    # TEMP: force a retry on first iteration to test the loop
    # if state["iteration"] == 0:
    #     return {
    #         "critic_verdict": "insufficient",
    #         "critic_feedback": "Missing information about recent developments in 2024 and 2025.",
    #         "iteration": state["iteration"] + 1
    #     }
    
    structured_llm = llm.with_structured_output(CriticOutput)
    
    research_text = "\n\n".join([
        f"Q: {r['question']}\nA: {r['summary']}"
        for r in state["research_results"]
    ])
    
    result = structured_llm.invoke([
        {
            "role": "system",
            "content": (
                "You are a critical reviewer. Assess whether the research "
                "sufficiently answers the original question. "
                "Return verdict as 'sufficient' or 'insufficient'. "
                "If insufficient, explain specifically what is missing. "
                "Return confidence as a decimal NUMBER between 0.0 and 1.0, "
                "for example 0.8 or 0.95. Never return confidence as a string."
            )
        },
        {
            "role": "user",
            "content": (
                f"Original Question: {state['question']}\n\n"
                f"Research Gathered:\n{research_text}"
            )
        }
    ])
    
    return {
        "critic_verdict": result.verdict,
        "critic_feedback": result.feedback,
        "critic_confidence": result.confidence,   # add this line
        "iteration": state["iteration"] + 1
    }


# ── Node 4: Writer ───────────────────────────────────────────
def writer_node(state: ResearchState) -> dict:
    research_text = "\n\n".join([
        f"Q: {r['question']}\nA: {r['summary']}"
        for r in state["research_results"]
    ])
    
    result = llm.invoke([
        {
            "role": "system",
            "content": (
                "You are an expert writer. Synthesize the research into a "
                "comprehensive, well-structured answer to the original question. "
                "Be factual, clear, and thorough."
            )
        },
        {
            "role": "user",
            "content": (
                f"Original Question: {state['question']}\n\n"
                f"Research:\n{research_text}"
            )
        }
    ])
    
    return {"final_answer": result.content}

def citation_verifier_node(state: ResearchState) -> dict:
    structured_llm = llm.with_structured_output(CitationVerifierOutput)

    research_text = "\n\n".join([
        f"[Source {i+1}]: {r['summary']}"
        for i, r in enumerate(state["research_results"])
    ])

    result = structured_llm.invoke([
        {
            "role": "system",
            "content": (
                "You are a fact-checker. Given a final answer and the research sources it was based on, "
                "extract the 3-5 most important factual claims from the answer. "
                "For each claim, check if it is supported by the provided sources. "
                "Return a list of verified_claims where each item has: "
                "'claim' (the statement), 'verified' (true/false), "
                "'source_index' (1-based index of supporting source, or 0 if none). "
                "Be strict — only mark as verified if the source explicitly supports it."
            )
        },
        {
            "role": "user",
            "content": (
                f"Final Answer:\n{state['final_answer']}\n\n"
                f"Research Sources:\n{research_text}"
            )
        }
    ])

    verified_count = sum(1 for c in result.verified_claims if c.get("verified"))
    total_count = len(result.verified_claims)
    print(f"[CITATIONS] {verified_count}/{total_count} claims verified")

    return {"verified_claims": result.verified_claims}

def followup_suggester_node(state: ResearchState) -> dict:
    structured_llm = llm.with_structured_output(FollowUpOutput)

    result = structured_llm.invoke([
        {
            "role": "system",
            "content": (
                "You are a research assistant. Based on the question and final answer provided, "
                "generate exactly 3 follow-up questions that would deepen the user's understanding. "
                "Questions should explore gaps, related topics, or practical implications. "
                "Keep each question concise and specific."
            )
        },
        {
            "role": "user",
            "content": (
                f"Original question: {state['question']}\n\n"
                f"Final answer summary: {state['final_answer'][:500]}..."
            )
        }
    ])

    print(f"[FOLLOWUP] Generated {len(result.follow_up_questions)} suggestions")
    return {"follow_up_questions": result.follow_up_questions}