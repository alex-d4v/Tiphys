import os
import pandas as pd
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from smart_manager.workflow import create_workflow
from neo4jmanager.manager import Neo4jManager
from neo4jmanager.task_operations import TaskOperations


# ── Ollama config ──────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME      = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)

if not os.path.exists("data"):
    os.makedirs("data")

#  LLM
def run_llm(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Send a prompt to model via Ollama and return the response text."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[LLM Error] {e}"

def run_llm_embeddings(input: str) -> list[float]:
    """Get embeddings from model via Ollama."""
    try:
        response = client.embeddings.create(
            model=MODEL_NAME,
            input=input,
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[LLM Embeddings Error] {e}")
        return []

# Main 
def main():
    print(f"Using model : {MODEL_NAME}")
    print(f"Ollama URL  : {OLLAMA_BASE_URL}\n")

    # Initialize Neo4j
    db_manager = Neo4jManager()
    db_manager.initialize_schema()
    db_ops = TaskOperations(db_manager)

    # Initial state - Only today's tasks for the operating DF
    tasks = db_ops.get_today_tasks()
    print(f"Loaded {len(tasks)} tasks for today from Neo4j")

    # Initialize workflow
    app = create_workflow(run_llm, run_llm_embeddings, db_ops)

    # Initial state
    state = {
        "tasks": tasks,
        "current_action": "",
        "exit_requested": False,
        "prev_message": None,
        "user_prev_message": None,
        "auto_func": True
    }

    try:
        # Run the graph until exit_requested is True or it finishes
        final_state = app.invoke(state, config={"recursion_limit": 500})
        tasks = final_state["tasks"]

    except KeyboardInterrupt:
        print("\nInterrupted...")
    except Exception as e:
        # we also need the traceback for debugging
        import traceback
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        # Shutdown check: ensure today's tasks were synced
        if isinstance(tasks, pd.DataFrame) and not tasks.empty:
            db_ops.store_tasks(tasks, embeddings_func=run_llm_embeddings)
            print("Today's tasks synced to Neo4j.")
        
        db_manager.close()
        print("Exiting...")

if __name__ == "__main__":
    main()