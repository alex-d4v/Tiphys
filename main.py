import os
import pandas as pd
import json
from openai import OpenAI

from smart_manager.workflow import create_workflow


# ── Ollama config ──────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME      = "mistral:7b"

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)

if not os.path.exists("data"):
    os.makedirs("data")

#  LLM
def run_llm(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Send a prompt to Mistral 7B via Ollama and return the response text."""
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
    """Get embeddings from Mistral 7B via Ollama."""
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

    tasks = []
    if os.path.exists("data/tasks.csv"):
        tasks = pd.read_csv("data/tasks.csv").to_dict(orient="records")
        for task in tasks:
            if isinstance(task["dependencies"], str) and task["dependencies"]:
                task["dependencies"] = json.loads(task["dependencies"])
            else:
                task["dependencies"] = []
            if "status" not in task or pd.isna(task.get("status")):
                task["status"] = "pending"
        print(f"Loaded {len(tasks)} existing tasks from data/tasks.csv")
    else:
        print("No existing tasks found. Starting fresh.")

    # Initialize workflow
    app = create_workflow(run_llm)

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
        if tasks:
            df = pd.DataFrame(tasks)
            df["dependencies"] = df["dependencies"].apply(json.dumps)
            df.to_csv("data/tasks.csv", index=False)
            print("Tasks saved to data/tasks.csv")
        else:
            # remove the file if there are no tasks to save
            if os.path.exists("data/tasks.csv"):
                os.remove("data/tasks.csv")
                print("No tasks to save. Existing data/tasks.csv removed.")
        print("Exiting...")

if __name__ == "__main__":
    main()