import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from cache import get_cached, set_cached
from vector_store import search_similar, store_result
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from langchain_tavily import TavilySearch
from .state import ResearchState, PlannerOutput, CriticOutput
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()
# pyrefly: ignore [missing-import]
from langchain_core.rate_limiters import InMemoryRateLimiter

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.5,   # 1 request every 2 seconds
    check_every_n_seconds=0.1,
    max_bucket_size=3
)

llm = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature=0,
    rate_limiter=rate_limiter
)
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

    # ── Tier 1: Redis exact match ─────────────────────────────
    cached = get_cached(question)
    if cached:
        print(f"[CACHE HIT] {question[:60]}...")
        return {"research_results": [cached]}

    # ── Tier 2: Qdrant semantic similarity ────────────────────
    similar = search_similar(question)
    if similar:
        # Store in Redis too so next exact hit is faster
        set_cached(question, similar)
        return {"research_results": [similar]}

    # ── Tier 3: Tavily + LLM (full research) ─────────────────
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
            "content": (
                f"Question: {question}\n\n"
                f"Search Results: {search_results}"
            )
        }
    ])

    result = {
        "question": question,
        "summary": summary.content
    }

    # ── Store in both layers ──────────────────────────────────
    set_cached(question, result)
    store_result(question, result)

    return {"research_results": [result]}


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
                "If insufficient, explain specifically what is missing."
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