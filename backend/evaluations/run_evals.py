"""
RAGAS Evaluation Runner for Multi-Agent Researcher
====================================================
Runs ALL 7 evaluators sequentially against the golden dataset
with built-in rate limiting to stay under Groq's free-tier TPM limits.

Metrics tracked:
  LLM-based:  Faithfulness, Answer Relevance, Context Precision, Context Recall
  Heuristic:  Citation Coverage, Answer Completeness, Retrieval Efficiency
"""

import os
import sys
import uuid
import time
import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Ensure backend directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langsmith import Client, evaluate
from graph_component.graph.graph import research_graph
from evaluations.evaluators import (
    faithfulness_evaluator,
    answer_relevance_evaluator,
    context_precision_evaluator,
    context_recall_evaluator,
    citation_coverage_evaluator,
    answer_completeness_evaluator,
    retrieval_efficiency_evaluator,
)

# Initialize LangSmith client
client = Client()

DATASET_NAME = "RAGAS_Golden_Dataset"

# ── Golden Dataset ──────────────────────────────────────────────
# Diverse questions covering factoid, comparative, and adversarial categories

GOLDEN_EXAMPLES = [
    # ── Factoid (direct answers) ────────────────────────────────
    {"question": "What is the capital of France?", "category": "factoid"},
    {"question": "Who won the 2024 Super Bowl and what was the final score?", "category": "factoid"},
    {"question": "What programming language is Python named after?", "category": "factoid"},
    {"question": "When was the first iPhone released?", "category": "factoid"},

    # ── Comparative (multi-entity analysis) ─────────────────────
    {"question": "What are the main differences between React and Vue.js for building web applications?", "category": "comparative"},
    {"question": "Compare PostgreSQL and MongoDB for a real-time analytics use case.", "category": "comparative"},
    {"question": "What are the trade-offs between microservices and monolithic architecture?", "category": "comparative"},

    # ── Exploratory (open-ended, requires synthesis) ────────────
    {"question": "How does retrieval-augmented generation (RAG) work and what are its benefits?", "category": "exploratory"},
    {"question": "What are the best practices for securing a REST API?", "category": "exploratory"},
    {"question": "How do large language models handle context windows and why does it matter?", "category": "exploratory"},
    {"question": "What is prompt engineering and what techniques are most effective?", "category": "exploratory"},

    # ── Current Events (tests live web search) ──────────────────
    {"question": "What are the latest developments in quantum computing in 2025?", "category": "current_events"},
    {"question": "What are the major AI regulations being discussed globally in 2025?", "category": "current_events"},

    # ── Multi-hop (requires combining multiple sources) ─────────
    {"question": "How does the transformer architecture used in GPT models differ from RNNs, and why did this shift happen?", "category": "multi_hop"},
    {"question": "What is LangChain, how does it relate to LangGraph, and when should you use one over the other?", "category": "multi_hop"},
    {"question": "Explain how vector databases work and why they are essential for RAG systems.", "category": "multi_hop"},

    # ── Adversarial (edge cases, should fail gracefully) ────────
    {"question": "What is the population of the dark side of the moon?", "category": "adversarial"},
    {"question": "Who won the 2030 FIFA World Cup?", "category": "adversarial"},
    {"question": "Explain the scientific consensus on time travel to the past.", "category": "adversarial"},
    {"question": "What is the stock price of OpenAI?", "category": "adversarial"},
]


def bootstrap_dataset():
    """Create or recreate the RAGAS golden dataset."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        # Check if the existing dataset has the right number of examples
        existing = client.read_dataset(dataset_name=DATASET_NAME)
        existing_examples = list(client.list_examples(dataset_id=existing.id))
        if len(existing_examples) == len(GOLDEN_EXAMPLES):
            print(f"✓ Dataset '{DATASET_NAME}' already exists with {len(existing_examples)} examples.")
            return
        else:
            print(f"⚠ Dataset has {len(existing_examples)} examples but expected {len(GOLDEN_EXAMPLES)}. Recreating...")
            client.delete_dataset(dataset_id=existing.id)

    print(f"Creating dataset '{DATASET_NAME}' with {len(GOLDEN_EXAMPLES)} examples...")
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="RAGAS-style golden dataset for evaluating the Multi-Agent Researcher."
    )

    for ex in GOLDEN_EXAMPLES:
        client.create_example(
            inputs={"question": ex["question"]},
            outputs={"category": ex["category"]},
            dataset_id=dataset.id,
        )
    print(f"✓ Dataset bootstrapped with {len(GOLDEN_EXAMPLES)} examples.")


# ── Graph Wrapper with Rate Limiting ────────────────────────────

def run_research_graph(inputs: dict) -> dict:
    """
    Wrapper that invokes the LangGraph with a delay between calls
    to stay under Groq's free-tier TPM limits.
    """
    question = inputs.get("question")
    if not question:
        raise ValueError("Input must contain a 'question' key.")

    # Wait between graph invocations to let TPM window reset
    print(f"\n{'='*60}")
    print(f"  Evaluating: {question[:70]}...")
    print(f"{'='*60}")
    time.sleep(5)  # 5-second cooldown before each graph run

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    start_time = time.time()
    result = research_graph.invoke(
        {"question": question},
        config=config
    )
    elapsed = time.time() - start_time

    # Inject timing metadata into the result for the latency evaluator
    result["_eval_latency_seconds"] = round(elapsed, 2)
    print(f"  → Completed in {elapsed:.1f}s")

    # Cooldown after graph run (the graph itself made many LLM calls)
    print(f"  → Cooling down 30s to reset TPM window for 8B and 70B models...")
    time.sleep(30)

    return result


def main():
    # 1. Ensure dataset exists
    bootstrap_dataset()

    # 2. All 7 evaluators
    evaluators = [
        # RAGAS LLM-based (4)
        faithfulness_evaluator,
        answer_relevance_evaluator,
        context_precision_evaluator,
        context_recall_evaluator,
        # Heuristic / zero-cost (3)
        citation_coverage_evaluator,
        answer_completeness_evaluator,
        retrieval_efficiency_evaluator,
    ]

    # 3. Run evaluation — strictly sequential
    print(f"\n🚀 Starting RAGAS evaluation against '{DATASET_NAME}'...")
    print(f"   Evaluators: {len(evaluators)} (4 LLM + 3 heuristic)")
    print(f"   Dataset size: {len(GOLDEN_EXAMPLES)} questions")
    print(f"   Mode: Sequential (max_concurrency=1)")
    print()

    results = evaluate(
        run_research_graph,
        data=DATASET_NAME,
        evaluators=evaluators,
        experiment_prefix="ragas-eval",
        max_concurrency=1,   # Strictly one at a time
        metadata={
            "version": "2.0",
            "eval_framework": "RAGAS",
            "graph_model": "llama-3.3-70b-versatile",
            "evaluator_model": "llama-3.1-8b-instant",
            "timestamp": datetime.now().isoformat()
        }
    )

    print("\n" + "="*60)
    print("  ✅ RAGAS Evaluation Complete!")
    print("  View results in your LangSmith dashboard.")
    print("="*60)


if __name__ == "__main__":
    missing = []
    if not os.getenv("LANGCHAIN_API_KEY"):
        missing.append("LANGCHAIN_API_KEY")
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")

    if missing:
        print(f"⚠️  Warning: Missing API keys: {', '.join(missing)}")
        print("   Evaluations may fail without these.")

    main()
