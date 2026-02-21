from typing import TypedDict, List, Literal, Annotated
import operator
import pandas as pd
import datetime
from langgraph.graph import StateGraph, END

# SIMPLE HARDCODED FUNCTIONS TO HANDLE TASKS AND INTERACTIONS , THE REAL LOGIC IS IN THE PROMPTS AND THE LLM RESPONSES
# handle_task contains functions to update task status and delete tasks based on user input and LLM responses
from manager.handle_task import update_task_status
# SMART MANAGER
# prompts to generate tasks , select tasks and change their status
from smart_manager.task_gen_prompt import (create_task_prompt, delete_task_prompt, 
                                           select_task_prompt , change_status_prompt)
# prompts for general messages and welcome message
from smart_manager.general_prompts import (create_general_message_prompt, 
                                           create_welcome_prompt,
                                           create_comment_tasks_prompt)
# prompt for tool selection
from smart_manager.tool_selection_prompt import select_action_prompt , select_search_tool_prompt , parametrize_tool_prompt
from smart_manager.collision_prompt import collision_check_prompt

from utils.parse_utils import input_task, parse_action_string, parse_general_json_bracketed_string, unpack_tasks
from utils.print_utils import print_tasks_table , print_update_message

# TypedDict for the state
class TaskManagerState(TypedDict):
    tasks: pd.DataFrame
    current_action: str
    exit_requested: bool
    prev_message : Annotated[str | None, lambda old, new: new]
    user_prev_message : str | None
    auto_func : bool 
    relevant_tasks: Annotated[pd.DataFrame, lambda old, new: pd.concat([old, new], ignore_index=True) if old is not None and new is not None else (new if new is not None else old)]
    planned_tasks: Annotated[pd.DataFrame | None, lambda old, new: new]
    can_proceed: bool

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
    #if not auto_func:
    #    user_msg = input("User Input : ").strip().lower()
    #else:
    #    user_msg = state.get("prev_message", "") or ""
    #    print(f"\n\nAuto-prompting with previous message\n\n")
    #    auto_func = False# this only happens once to pass the initial welcome message to the router for better context

    user_msg = input("User Input : ").strip().lower()
    response = run_llm_func(prompt=user_msg, system_prompt=select_action_prompt())
    # extract json first
    response_json = parse_general_json_bracketed_string(response)
    
    prev_message = response_json.get("message", "")
    action = parse_action_string(response_json.get("action", ""))

    return {"current_action": action , "prev_message" : prev_message, "user_prev_message": user_msg, "auto_func": auto_func}

def router(state: TaskManagerState, run_llm_func) -> Literal["generate_tasks", "update_status", "list_tasks", "delete_tasks", "comment_tasks", "exit", "menu"]:
    action = state.get("current_action", "")
    
    valid_actions = ['generate_tasks', 'update_status', 'list_tasks', 'delete_tasks', 'comment_tasks', 'exit', 'menu']
    
    if action in valid_actions:
        return action
    else:
        # General message handling
        print("="*50)
        response = run_llm_func(
            prompt=state.get("user_prev_message", "No previous message."),
            system_prompt=create_general_message_prompt(prev_message=state.get("prev_message", ""))
        )
        print(f"\n\n{response}\n\n")
        print("="*50)
        # Update state with response - this fixes the repeated messages
        state["prev_message"] = response
        return "menu"

def generate_tasks_node(state: TaskManagerState, run_llm_func) -> dict:
    user_msg = state.get("user_prev_message", "")
    if not user_msg:
        print("No valid task entered.")
        return {"planned_tasks": pd.DataFrame()}

    # Generate tasks
    response = run_llm_func(prompt=user_msg, system_prompt=create_task_prompt())
    temp_tasks = unpack_tasks(response)
    
    if not temp_tasks:
        print("No tasks generated. Check response format.")
        return {"planned_tasks": pd.DataFrame()}
    
    planned_df = pd.DataFrame(temp_tasks)
    return {"planned_tasks": planned_df}

def search_node(state: TaskManagerState, run_llm_func, db_ops_search) -> dict:
    """Search for potentially colliding nodes using dynamic tool selection."""
    user_msg = state.get("user_prev_message", "")
    planned_tasks = state.get("planned_tasks", None)
    
    # We want to search for each task in parallel or collectively.
    # We'll pass both user message and planned tasks to the search selection prompt.
    if not planned_tasks is None and not planned_tasks.empty:
        planned_tasks_str = "Planned Tasks for creation:\n" + "\n".join(print_update_message(planned_tasks, verbose=False))
    else: 
        planned_tasks_str = ""
    search_context = f"User Request: {user_msg} \n\n {planned_tasks_str}"
    
    available_tools = db_ops_search.get_available_tools()
    tool_signatures = [f"{t['signature']}: {t['description']}" for t in available_tools]
    print(f"\nThere are {len(available_tools)} available search tools for finding relevant tasks in the database.\n")
    selection_prompt = select_search_tool_prompt(tool_signatures)
    
    # Pass search context as the prompt
    response = run_llm_func(prompt=search_context, system_prompt=selection_prompt)
    response_json = parse_general_json_bracketed_string(response)
    selected_tool_names = response_json.get("selected_tools", [])
    justification = response_json.get("justification", "")
    # which tools ?
    print(f"\nList of selected tools for searching relevant tasks: {'\n -'.join(selected_tool_names)}\n")
    print(f"🧠 Tool Selection: {justification}")

    relevant_tasks = None
    
    for tool_name in selected_tool_names:
        tool_info = next((t for t in available_tools if t['name'] == tool_name), None)
        if not tool_info: continue
        
        p_prompt = parametrize_tool_prompt(tool_info)
        arg_response = run_llm_func(prompt=search_context, system_prompt=p_prompt)
        arg_json = parse_general_json_bracketed_string(arg_response)
        # we have the value for the parameters, we can now call the tool function with these parameters
        args = arg_json.get("args", {})
        try:
            tool_func = getattr(db_ops_search, tool_name)
            result = tool_func(**args)
            
            if isinstance(result, pd.DataFrame) and not result.empty:
                if relevant_tasks is None:
                    relevant_tasks = result
                else:
                    relevant_tasks = pd.concat([relevant_tasks, result], ignore_index=True)
                print(f"Tool '{tool_name}' found {len(result)} tasks")
        except Exception as e:
            print(f"Error executing tool '{tool_name}': {e}")
    
    if relevant_tasks is not None and not relevant_tasks.empty:
        relevant_tasks = relevant_tasks.drop_duplicates(subset=['id'], keep='first')
        return {"relevant_tasks": relevant_tasks}
    
    print("No potential matches in database.")
    return {"relevant_tasks": pd.DataFrame()}

def check_collision_with_existing_tasks(state: TaskManagerState, relevant_tasks: pd.DataFrame, run_llm_func) -> dict:
    """Check if new task collides with existing tasks."""
    user_msg = state.get("user_prev_message", "")
    planned_tasks = state.get("planned_tasks", pd.DataFrame())
    
    if planned_tasks.empty:
        return {"can_proceed": True}
    
    if relevant_tasks is None or relevant_tasks.empty:
        print("No existing tasks identified as potentially colliding. Proceeding with creation.")
        return {"can_proceed": True}
    
    # Check collision via LLM
    print(f"\nTotal unique tasks found that might collide: {len(relevant_tasks)}\n")
    planned_str = "\n".join(print_update_message(planned_tasks, verbose=False))
    relevant_str = "\n".join(print_update_message(relevant_tasks, verbose=False))
    
    collision_prompt_str = collision_check_prompt(planned_str, relevant_str)
    collision_response = run_llm_func(prompt=user_msg, system_prompt=collision_prompt_str)
    collision_json = parse_general_json_bracketed_string(collision_response)
    
    collision_exists = collision_json.get("collision_exists", False)
    can_proceed = collision_json.get("can_proceed", True)
    justification = collision_json.get("justification", "No justification provided.")
    print(f"🧠 Collision Check: {justification}")

    if not can_proceed:
        print("Task creation BLOCKED due to collision.")
        return {"can_proceed": False, "prev_message": f"Task creation blocked: {justification}"}
    else:
        print("Collision noted but proceeding with creation.")
        return {"can_proceed": True, "prev_message": f"{justification}"}
    

def create_tasks_from_user_input(state: TaskManagerState, run_llm_func, run_llm_embeddings_func, db_ops) -> TaskManagerState:
    can_proceed = state.get("can_proceed", True)
    planned_tasks = state.get("planned_tasks", pd.DataFrame())
    
    if not can_proceed:
        # Prev message should already contain the justification
        return {"tasks": state["tasks"], "planned_tasks": pd.DataFrame()}

    if planned_tasks.empty:
        print("No tasks were planned for creation.")
        return {"tasks": state["tasks"]}
    
    # Store to DB
    db_ops.store_tasks(planned_tasks, embeddings_func=run_llm_embeddings_func)
    
    print("="*50)
    print(f"\n\nSuccessfully added {len(planned_tasks)} tasks to Database\n\n")
    print_update_message(planned_tasks)
    print("="*50)
    
    # Update operating DF (only today's tasks)
    import datetime
    today = datetime.date.today().isoformat()
    today_new_tasks = planned_tasks[planned_tasks["date"] == today]
    
    user_corpus = f"""
        User : I have just added {len(planned_tasks)} Tasks.
        Tasks detail :
        {print_update_message(planned_tasks, verbose=False)}
    """
    general_message = run_llm_func(prompt=user_corpus, system_prompt=create_general_message_prompt())

    print(f"\n\n{general_message}\n\n")

    # Important : clear planned_tasks to avoid re-adding
    return {"tasks": pd.concat([state["tasks"], today_new_tasks], ignore_index=True), "planned_tasks": pd.DataFrame()}

def update_status_node(state: TaskManagerState , run_llm_func, db_ops, db_ops_search) -> TaskManagerState:
    # Retrieve relevant tasks via vector search
    user_msg = state.get("user_prev_message", "")
    relevant_tasks = db_ops_search.get_relevant_tasks_by_query(user_msg, top_k=10)
    
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

def comment_tasks_node(state: TaskManagerState, run_llm_func, db_ops_search) -> TaskManagerState:
    # Radius of 12h
    now = datetime.datetime.now()
    start_dt = now - datetime.timedelta(hours=12)
    end_dt = now + datetime.timedelta(hours=12)
    
    start_date = start_dt.date().isoformat()
    start_time = start_dt.time().strftime("%H:%M")
    end_date = end_dt.date().isoformat()
    end_time = end_dt.time().strftime("%H:%M")
    
    recent_tasks = db_ops_search.get_tasks_by_time_range(start_date, end_date,start_time, end_time, limit=10)
    
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

def delete_tasks_node(state: TaskManagerState , run_llm_func, db_ops, db_ops_search) -> TaskManagerState:

    user_msg = state.get("user_prev_message", "")
    print(f"Searching for tasks to delete based on user intent: '{user_msg}'...")
    
    # 1. Global search via embeddings to find deletion candidates (retrieve top 10)
    relevant_tasks = db_ops_search.get_relevant_tasks_by_query(user_msg, top_k=10)
    
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

def create_workflow(run_llm_func, run_llm_embeddings_func, db_ops , db_ops_search=None):
    workflow = StateGraph(TaskManagerState)

    # Add nodes
    workflow.add_node("initial", lambda state: initial_node(state , run_llm_func))
    workflow.add_node("menu", lambda state: print_menu_node(state, run_llm_func))
    # Task creation flow
    workflow.add_node("generate_tasks", lambda state: generate_tasks_node(state, run_llm_func))
    workflow.add_node("search", lambda state: search_node(state, run_llm_func, db_ops_search))
    workflow.add_node("check_collision", lambda state: check_collision_with_existing_tasks(state, state.get("relevant_tasks", pd.DataFrame()), run_llm_func))
    workflow.add_node("create_tasks", lambda state: create_tasks_from_user_input(state, run_llm_func, run_llm_embeddings_func, db_ops))

    workflow.add_node("update_status", lambda state: update_status_node(state, run_llm_func, db_ops, db_ops_search))
    workflow.add_node("delete_tasks", lambda state: delete_tasks_node(state, run_llm_func, db_ops, db_ops_search))
    workflow.add_node("comment_tasks", lambda state: comment_tasks_node(state, run_llm_func, db_ops_search))
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
    workflow.add_edge("initial", "comment_tasks")

    # workflow on generating tasks
    workflow.add_edge("generate_tasks", "search")
    workflow.add_edge("search", "check_collision")
    workflow.add_conditional_edges(
        "check_collision",
        lambda state: "create_tasks" if state.get("can_proceed", True) else "menu",
        {
            "create_tasks": "create_tasks",
            "menu": "menu"
        }
    )

    workflow.add_edge("create_tasks", "menu")
    workflow.add_edge("update_status", "menu")
    workflow.add_edge("list_tasks", "menu")
    workflow.add_edge("delete_tasks", "menu")
    workflow.add_edge("comment_tasks", "menu")
    workflow.add_edge("exit", END)

    return workflow.compile()
