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

    tasks = pd.DataFrame()
    if os.path.exists("data/tasks.csv"):
        tasks = pd.read_csv("data/tasks.csv")
        
        # Ensure dependencies are list objects
        if "dependencies" in tasks.columns:
            def ensure_list(x):
                if isinstance(x, str):
                    try:
                        return json.loads(x)
                    except:
                        return []
                return x if isinstance(x, list) else []
            tasks["dependencies"] = tasks["dependencies"].apply(ensure_list)
        else:
            tasks["dependencies"] = [[] for _ in range(len(tasks))]

        # Fill missing values and ensure columns exist
        cols_to_fill = {
            "status": "pending",
            "priority": "medium",
            "date": "9999-12-31",
            "time": "23:59"
        }
        for col, val in cols_to_fill.items():
            if col not in tasks.columns:
                tasks[col] = val
            tasks[col] = tasks[col].fillna(val)
        
        if "started_at" not in tasks.columns: tasks["started_at"] = None
        if "ended_at" not in tasks.columns: tasks["ended_at"] = None

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
        if isinstance(tasks, pd.DataFrame) and not tasks.empty:
            df_to_save = tasks.copy()
            # Convert list dependencies back to JSON strings for CSV
            df_to_save["dependencies"] = df_to_save["dependencies"].apply(json.dumps)
            df_to_save.to_csv("data/tasks.csv", index=False)
            print("Tasks saved to data/tasks.csv")
        else:
            # remove the file if there are no tasks to save
            if os.path.exists("data/tasks.csv"):
                os.remove("data/tasks.csv")
                print("No tasks to save. Existing data/tasks.csv removed.")
        print("Exiting...")

if __name__ == "__main__":
    main()