import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from neo4jmanager.task_search_operations import TaskSearchOperations
from smart_manager.workflow import create_workflow
from neo4jmanager.manager import Neo4jManager
from neo4jmanager.task_operations import TaskOperations

# configure logging - set to WARNING to hide internal DB and connection logs
import logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Keep our main logger at INFO if you want to see standard app messages
logger.setLevel(logging.INFO)

# Suppress verbose third-party logs
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# ── Ollama config ──────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME      = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)

# DEPRECATED : we now use DB
#if not os.path.exists("data"):
#    os.makedirs("data")

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
        logger.error(f"[LLM Embeddings Error] {e}")
        return []

# Main 
def main():
    logger.info(f"Using model : {MODEL_NAME}")
    logger.info(f"Ollama URL  : {OLLAMA_BASE_URL}\n")

    # Initialize Neo4j
    db_manager = Neo4jManager()
    db_manager.initialize_schema()
    db_ops = TaskOperations(db_manager)
    db_ops_search = TaskSearchOperations(db_manager, embeddings_func=run_llm_embeddings)  # Pass embeddings func to search operations
    # when we have messed up xD
    #db_manager.clear_database(confirm=True)

    # Initial state - Only today's tasks for the operating DF
    tasks = db_ops.get_today_tasks()
    logger.info(f"Loaded {len(tasks)} tasks for today from Neo4j")

    # Initialize workflow
    app = create_workflow(run_llm, run_llm_embeddings, db_ops , db_ops_search)

    # Initial state
    state = {
        "tasks": tasks,
        "current_action": "",
        "exit_requested": False,
        "prev_message": None,
        "user_prev_message": None,
        "auto_func": True,
        "relevant_tasks": pd.DataFrame(),
        "can_proceed": True
    }

    try:
        # Run the graph until exit_requested is True or it finishes
        final_state = app.invoke(state, config={"recursion_limit": 500})
        tasks = final_state["tasks"]

    except KeyboardInterrupt:
        logger.info("Interrupted...")
    except Exception as e:
        # we also need the traceback for debugging
        import traceback
        logger.error(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        # Shutdown check: ensure today's tasks were synced
        if isinstance(tasks, pd.DataFrame) and not tasks.empty:
            db_ops.store_tasks(tasks, embeddings_func=run_llm_embeddings)
            logger.info("Today's tasks synced to Neo4j.")
        if isinstance(tasks, pd.DataFrame) and tasks.empty:
            logger.info("No tasks to sync.")
            # delete all tasks from neo4j that are scheduled for today since we have no tasks for today in the df
            deleted_count = db_ops.delete_all_tasks()
            logger.info(f"Deleted {deleted_count} tasks from Neo4j.")
        
        db_manager.close()
        logger.info("Exiting...")

if __name__ == "__main__":
    main()