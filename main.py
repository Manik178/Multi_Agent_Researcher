from graph_component.graph.graph import research_graph
import uuid

def run(question: str, thread_id: str = None):
    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = {"configurable": {"thread_id": thread_id}}

    print(f"\n🔍 Question: {question}")
    print(f"🧵 Thread ID: {thread_id}")
    print("─" * 50)

    result = research_graph.invoke(
        {"question": question},
        config=config
    )

    print(f"📋 Sub-questions explored:")
    for i, q in enumerate(result["sub_questions"], 1):
        print(f"  {i}. {q}")

    print(f"\n🔄 Iterations: {result['iteration']}")
    print(f"✅ Critic verdict: {result['critic_verdict']}")
    print(f"\n📝 Final Answer:\n{result['final_answer']}")

    return thread_id


if __name__ == "__main__":
    # First question
    tid = run("What is the current state of fusion energy research?")

    # Follow-up on same thread — graph remembers previous state
    print("\n" + "="*50)
    print("FOLLOW-UP QUESTION ON SAME THREAD")
    print("="*50)
    run("What are the main challenges holding it back?", thread_id=tid)