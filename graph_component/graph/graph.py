from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from .state import ResearchState
from .nodes import planner_node, researcher_node, critic_node, writer_node
import os

DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/research_agent"
)


def dispatch_researchers(state: ResearchState) -> list[Send]:
    return [
        Send("researcher", {"sub_questions": [q], "research_results": []})
        for q in state["sub_questions"]
    ]


def should_continue(state: ResearchState) -> str:
    if state["critic_verdict"] == "sufficient" or state["iteration"] >= 2:
        return "writer"
    return "planner"


import psycopg

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", dispatch_researchers, ["researcher"])
    graph.add_edge("researcher", "critic")
    graph.add_conditional_edges(
        "critic",
        should_continue,
        {"writer": "writer", "planner": "planner"}
    )
    graph.add_edge("writer", END)

    # ── PostgreSQL checkpointer ───────────────────────────────
    # Setup needs autocommit=True for CREATE INDEX CONCURRENTLY
    # ── PostgreSQL checkpointer ───────────────────────────────
    connection_pool = ConnectionPool(
        conninfo=DB_URI,
        max_size=10,
        open=True,
        kwargs={"autocommit": True}
    )
    checkpointer = PostgresSaver(connection_pool)
    checkpointer.setup()

    return graph.compile(checkpointer=checkpointer)


research_graph = build_graph()