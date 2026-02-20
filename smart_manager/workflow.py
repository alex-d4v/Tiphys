from typing import TypedDict, List, Literal, Annotated
import operator
import pandas as pd
import datetime
from langgraph.graph import StateGraph, END

# SIMPLE HARDCODED FUNCTIONS TO HANDLE TASKS AND INTERACTIONS , THE REAL LOGIC IS IN THE PROMPTS AND THE LLM RESPONSES
# handle_task contains functions to update task status and delete tasks based on user input and LLM responses
from manager.handle_task import delete_task_by_id, update_task_status
# SMART MANAGER
# prompts to generate tasks , select tasks and change their status
from smart_manager.task_gen_prompt import (create_task_prompt, delete_task_prompt, 
                                           select_task_prompt , change_status_prompt)
# prompts for general messages and welcome message
from smart_manager.general_prompts import (create_general_message_prompt, 
                                           create_welcome_prompt,
                                           create_comment_tasks_prompt)
# prompt for tool selection
from smart_manager.tool_selection_prompt import select_action_prompt
from smart_manager.collision_prompt import collision_check_prompt

from utils.parse_utils import input_task, parse_action_string, parse_general_json_bracketed_string, unpack_tasks
from utils.print_utils import print_tasks_table , print_update_message

# TypedDict for the state
class TaskManagerState(TypedDict):
    tasks: pd.DataFrame
    current_action: str
    exit_requested: bool
    prev_message : str | None
    user_prev_message : str | None
    auto_func : bool = True

def initial_node(state: TaskManagerState , run_llm_func) -> TaskManagerState:
    # we just invoke the llm to get a welcome message or initial tasks if needed
    tasks = state.get("tasks")
    if tasks is None: tasks = pd.DataFrame()

    prompt = create_welcome_prompt(
        user_name="Alex Ntavlouros",
        tasks=tasks
    )

    wlc_message = run_llm_func(prompt="Hello", system_prompt=prompt)
    print("" + "="*50)
    print(f"\n\n{wlc_message}\n\n")
    print("="*50 + "\n")
    state["prev_message"] = wlc_message

    return state

def list_tasks_node(state: TaskManagerState, db_ops) -> TaskManagerState:
    all_tasks = db_ops.get_tasks()
    if not all_tasks.empty:
        print_tasks_table(all_tasks)
    else:
        print("No tasks found in Database.")
    return state

def print_menu_node(state: TaskManagerState , run_llm_func) -> TaskManagerState:

    user_msg = ""
    auto_func = state.get("auto_func", False)
    if not auto_func:
        user_msg = input("User Input : ").strip().lower()
    else:
        user_msg = state.get("prev_message", "") or ""
        print(f"\n\nAuto-prompting with previous message\n\n")
        auto_func = False# this only happens once to pass the initial welcome message to the router for better context

    response = run_llm_func(prompt=user_msg, system_prompt=select_action_prompt())
    # extract json first
    response_json = parse_general_json_bracketed_string(response)
    
    prev_message = response_json.get("message", "")
    action = parse_action_string(response_json.get("action", ""))

    return {"current_action": action , "prev_message" : prev_message, "user_prev_message": user_msg, "auto_func": auto_func}

def router(state: TaskManagerState , run_llm_func) -> Literal["generate_tasks", "update_status", "list_tasks", "exit", "menu", "comment_tasks"]:
    action = state.get("current_action", "")
    if action == 'generate_tasks':
        return "generate_tasks"
    elif action == 'update_status':
        return "update_status"
    elif action == 'list_tasks':
        return "list_tasks"
    elif action == 'delete_tasks':
        return "delete_tasks"
    elif action == 'comment_tasks':
        return "comment_tasks"
    elif action == 'exit':
        return "exit"
    elif action == 'menu':
        return "menu"
    else:
        print("="*50)
        response = run_llm_func(prompt=state.get("user_prev_message", "No previous message."), 
                                system_prompt=create_general_message_prompt(prev_message=state.get("prev_message", ""))
                                )
        print(f"\n\n{response}\n\n")
        print("="*50)
        return "menu"

def generate_tasks_node(state: TaskManagerState, run_llm_func, run_llm_embeddings_func, db_ops):

    user_msg = state.get("user_prev_message", None)
    task_desc = ""
    if not user_msg:
        task_desc = input_task()
        if not task_desc:
            print("No valid task entered.")
            return {"tasks": state["tasks"]}
    else:
        task_desc = user_msg

    # Collision Check Step (Intermediate step)
    # Embed the query
    query_embedding = run_llm_embeddings_func(task_desc)
    # Retrieve relevant tasks from DB
    relevant_tasks = db_ops.get_relevant_tasks_by_query(query_embedding, top_k=10)
    
    if not relevant_tasks.empty:
        # Check collision via LLM
        relevant_str = "\n".join(print_update_message(relevant_tasks, verbose=False))
        collision_prompt = collision_check_prompt(task_desc, relevant_str)
        collision_response = run_llm_func(prompt=collision_prompt, system_prompt="You are a meticulous task reviewer.")
        collision_json = parse_general_json_bracketed_string(collision_response)
        
        if collision_json.get("collision_exists", False):
            print("\n" + "="*50)
            print(f"{collision_json.get('justification', 'No justification provided.')}")
            print("="*50 + "\n")
            if not collision_json.get("can_proceed", False):
                return {"tasks": state["tasks"]}
    
    # Generate tasks
    response = run_llm_func(prompt=task_desc, system_prompt=create_task_prompt())
    
    temp_tasks = unpack_tasks(response)
    if not temp_tasks:
        print("No tasks unpacked. Check response format.")
        return {"tasks": state["tasks"]}
    
    # Store to DB
    new_tasks_df = pd.DataFrame(temp_tasks)
    db_ops.store_tasks(new_tasks_df, embeddings_func=run_llm_embeddings_func)
    
    print("="*50)
    print(f"\n\nAdding {len(temp_tasks)} tasks to Database\n\n")
    print_update_message(new_tasks_df)# print the new tasks in a nice format for the user to see what was added
    print("="*50)
    
    # Update operating DF (only today's tasks)
    import datetime
    today = datetime.date.today().isoformat()
    today_new_tasks = new_tasks_df[new_tasks_df["date"] == today]
    
    user_corpus = f"""
        User : I have just added some tasks with the follwing description :
        {print_update_message(new_tasks_df, verbose=False)}
    """
    general_message = run_llm_func(prompt=user_corpus, 
                                   system_prompt=create_general_message_prompt())

    print(f"\n\n{general_message}\n\n")

    return {"tasks": pd.concat([state["tasks"], today_new_tasks], ignore_index=True)}

def update_status_node(state: TaskManagerState , run_llm_func, run_llm_embeddings_func, db_ops):
    # Retrieve relevant tasks via vector search
    user_msg = state.get("user_prev_message", "")
    query_embedding = run_llm_embeddings_func(user_msg)
    relevant_tasks = db_ops.get_relevant_tasks_by_query(query_embedding, top_k=10)
    
    if relevant_tasks.empty:
        print("No relevant tasks found in Database for update.")
        return state
    
    # First Phase : Select relevant tasks based on user input
    corpus = print_update_message(relevant_tasks)
    # join into one string for LLM understanding
    corpus_str = user_msg + "\n\nThis is a sheet of my tasks :\n\n" + "\n\n".join(corpus)

    response = run_llm_func(prompt=corpus_str, system_prompt=select_task_prompt())
    # parse response to get selected tasks and justification
    response_json = parse_general_json_bracketed_string(response)
    selected_tasks = response_json.get("selected_tasks", [])
    justification = response_json.get("justification", "")
    print(f"🧠 {justification}")

    # validate they exist in relevant tasks
    valid_tasks_df = relevant_tasks[relevant_tasks["id"].astype(str).isin([str(tid) for tid in selected_tasks])]
    
    if valid_tasks_df.empty:
        print("No valid tasks selected for update.")
        return state
    
    # Second Phase : Get new status for selected tasks
    valid_task_corpus = print_update_message(valid_tasks_df)
    user_prompt = f"""
    User : {user_msg}
    Selected Tasks : {"\n\n".join(valid_task_corpus)}
    """
    response = run_llm_func(prompt=user_prompt,
                            system_prompt = change_status_prompt(justification))
    response_json = parse_general_json_bracketed_string(response)
    updated_tasks_info = response_json.get("updated_tasks", [])
    update_justification = response_json.get("justification", "")
    
    state['prev_message'] = update_justification
    
    print("="*50)
    print(f"🧠 {update_justification}")
    print("="*50)

    # validate updated tasks info
    df = state["tasks"].copy()
    for update_info in updated_tasks_info:
        task_id = update_info.get("id")
        new_status = update_info.get("new_status")
        
        # Update the task status in the DataFrame and DB
        df = update_task_status(df, str(task_id), str(new_status), db_ops=db_ops)
        print(f"Task ID {task_id} status updated to {new_status}.")
    
    state["tasks"] = df
    return state

def comment_tasks_node(state: TaskManagerState, run_llm_func, db_ops) -> TaskManagerState:
    # Radius of 1h
    now = datetime.datetime.now()
    start_dt = now - datetime.timedelta(hours=1)
    end_dt = now + datetime.timedelta(hours=1)
    
    start_date = start_dt.date().isoformat()
    start_time = start_dt.time().strftime("%H:%M")
    end_date = end_dt.date().isoformat()
    end_time = end_dt.time().strftime("%H:%M")
    
    recent_tasks = db_ops.get_tasks_by_time_range(start_date, start_time, end_date, end_time, limit=10)
    
    if recent_tasks.empty:
        print("No tasks found in the last/next 1h range.")
        return state
        
    print(f"Found {len(recent_tasks)} tasks within 1h radius of current time.")
    print_tasks_table(recent_tasks)
    
    # Send to LLM for commenting
    prompt = create_comment_tasks_prompt(recent_tasks)
    response = run_llm_func(prompt="What do you think of my current tasks?", system_prompt=prompt)
    
    print("\n" + "="*50)
    print(f"\n{response}\n")
    print("="*50 + "\n")
    
    state["prev_message"] = response
    return state

def delete_tasks_node(state: TaskManagerState , run_llm_func, run_llm_embeddings_func, db_ops) -> TaskManagerState:

    user_msg = state.get("user_prev_message", "")
    print(f"Searching for tasks to delete based on user intent: '{user_msg}'...")
    
    # 1. Global search via embeddings to find deletion candidates (retrieve top 10)
    query_embedding = run_llm_embeddings_func(user_msg)
    relevant_tasks = db_ops.get_relevant_tasks_by_query(query_embedding, top_k=10)
    
    if relevant_tasks.empty:
        print("No relevant tasks found in database for deletion.")
        # User-friendly message for no tasks found
        no_tasks_corpus = f"User wanted to delete some tasks with the following intent: '{user_msg}', but no relevant tasks were found in the database."
        general_message = run_llm_func(prompt=no_tasks_corpus, system_prompt=create_general_message_prompt())
        print(f"\n\n{general_message}\n\n")
        return state

    # 2. Use LLM to select from global candidates
    corpus = print_update_message(relevant_tasks, verbose=False)
    corpus_str = user_msg + "\n\nRelevant tasks found in database:\n\n" + "\n\n".join(corpus)
    
    response = run_llm_func(prompt=corpus_str, system_prompt=delete_task_prompt())
    response_json = parse_general_json_bracketed_string(response)
    selected_tasks = response_json.get("deleted_tasks", [])
    justification = response_json.get("justification", "")
    
    if not selected_tasks:
        print(f"🧠 {justification} (No tasks selected for deletion)")
        # Show general message justification
        general_message = run_llm_func(prompt=f"Justification for not deleting anything: {justification}", system_prompt=create_general_message_prompt())
        print(f"\n\n{general_message}\n\n")
        return state

    print("="*50)
    print(f"🧠 {justification}")
    print("="*50)

    # 3. Synchronize Deletion: DB and Local Operating DF
    # Batch delete from Neo4j
    deleted_count = db_ops.delete_tasks([str(tid) for tid in selected_tasks])
    print(f"Synced {deleted_count} deletions to Database.")
    
    # Update local operating DF
    df = state["tasks"].copy()
    initial_len = len(df)
    for did in selected_tasks:
        df = df[df["id"].astype(str) != str(did)]
    
    if len(df) < initial_len:
        print(f"Updated local operating DF (removed {initial_len - len(df)} today's tasks).")
    
    state["tasks"] = df.reset_index(drop=True)
    return state

def exit_node(state: TaskManagerState):
    return {"exit_requested": True}

def create_workflow(run_llm_func, run_llm_embeddings_func, db_ops):
    workflow = StateGraph(TaskManagerState)

    # Add nodes
    workflow.add_node("initial", lambda state: initial_node(state , run_llm_func))
    workflow.add_node("menu", lambda state: print_menu_node(state, run_llm_func))
    workflow.add_node("generate_tasks", lambda state: generate_tasks_node(state, run_llm_func, run_llm_embeddings_func, db_ops))
    workflow.add_node("update_status", lambda state: update_status_node(state, run_llm_func, run_llm_embeddings_func, db_ops))
    workflow.add_node("delete_tasks", lambda state: delete_tasks_node(state, run_llm_func, run_llm_embeddings_func, db_ops))
    workflow.add_node("comment_tasks", lambda state: comment_tasks_node(state, run_llm_func, db_ops))
    workflow.add_node("list_tasks", lambda state: list_tasks_node(state, db_ops))
    workflow.add_node("exit", exit_node)

    # Entry point
    workflow.set_entry_point("initial")

    # Conditional edges from menu
    workflow.add_conditional_edges(
        "menu",
        lambda state: router(state, run_llm_func),
        {
            "generate_tasks": "generate_tasks",
            "update_status": "update_status",
            "list_tasks": "list_tasks",
            "delete_tasks": "delete_tasks",
            "comment_tasks": "comment_tasks",
            "exit": "exit",
            "menu": "menu",
        }
    )

    # Back to menu after actions
    workflow.add_edge("initial", "menu")
    workflow.add_edge("generate_tasks", "menu")
    workflow.add_edge("update_status", "menu")
    workflow.add_edge("list_tasks", "menu")
    workflow.add_edge("delete_tasks", "menu")
    workflow.add_edge("comment_tasks", "menu")
    workflow.add_edge("exit", END)

    return workflow.compile()
