from typing import TypedDict, List, Literal, Annotated
import operator
import pandas as pd
from langgraph.graph import StateGraph, END

# SIMPLE HARDCODED FUNCTIONS TO HANDLE TASKS AND INTERACTIONS , THE REAL LOGIC IS IN THE PROMPTS AND THE LLM RESPONSES
# handle_task contains functions to update task status and delete tasks based on user input and LLM responses
from manager.handle_task import delete_task_by_id, update_task_status
# SMART MANAGER
# prompts to generate tasks , select tasks and change their status
from smart_manager.task_gen_prompt import (create_task_prompt, delete_task_prompt, 
                                           select_task_prompt , change_status_prompt)
# prompts for general messages and welcome message
from smart_manager.general_prompts import create_general_message_prompt, create_welcome_prompt
# prompt for tool selection
from smart_manager.tool_selection_prompt import select_action_prompt

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

def list_tasks_node(state: TaskManagerState) -> TaskManagerState:
    if not state["tasks"].empty:
        print_tasks_table(state["tasks"])
    else:
        print("No tasks found.")
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

def router(state: TaskManagerState , run_llm_func) -> Literal["generate_tasks", "update_status", "list_tasks", "exit", "menu"]:
    action = state.get("current_action", "")
    if action == 'generate_tasks':
        return "generate_tasks"
    elif action == 'update_status':
        return "update_status"
    elif action == 'list_tasks':
        return "list_tasks"
    elif action == 'delete_tasks':
        return "delete_tasks"
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

def generate_tasks_node(state: TaskManagerState, run_llm_func):

    user_msg = state.get("user_prev_message", None)
    task_desc = ""
    if not user_msg:
        task_desc = input_task()
        if not task_desc:
            print("No valid task entered.")
            return {"tasks": state["tasks"]}
    else:
        task_desc = user_msg

    response = run_llm_func(prompt=task_desc, system_prompt=create_task_prompt())
    
    temp_tasks = unpack_tasks(response)
    if not temp_tasks:
        print("No tasks unpacked. Check response format.")
        return {"tasks": state["tasks"]}
    
    print("="*50)
    print(f"\n\nAdding {len(temp_tasks)} tasks\n\n")
    print_update_message(pd.DataFrame(temp_tasks))# print the new tasks in a nice format for the user to see what was added
    print("="*50)
    
    # Convert to DF for print utility
    new_tasks_df = pd.DataFrame(temp_tasks)
    user_corpus = f"""
        User : I have just added some tasks with the follwing description :
        {print_update_message(new_tasks_df, verbose=False)}
    """
    general_message = run_llm_func(prompt=user_corpus, 
                                   system_prompt=create_general_message_prompt())

    print(f"\n\n{general_message}\n\n")

    return {"tasks": pd.concat([state["tasks"], new_tasks_df], ignore_index=True)}

def update_status_node(state: TaskManagerState , run_llm_func):
    # Pass a copy to avoid side effects
    df = state["tasks"].copy()
    if df.empty:
        print("No tasks available to update.")
        return {"tasks": df}
    
    # First Phase : Select relevant tasks based on user input
    corpus = print_update_message(df)
    # join into one string for LLM understanding
    corpus_str = str(state.get("user_prev_message", "")) + "\n\nThis is a sheet of my tasks :\n\n" + "\n\n".join(corpus)

    response = run_llm_func(prompt=corpus_str, system_prompt=select_task_prompt())
    # parse response to get selected tasks and justification
    response_json = parse_general_json_bracketed_string(response)
    selected_tasks = response_json.get("selected_tasks", [])
    justification = response_json.get("justification", "")
    print(f"🧠 {justification}")

    # validate they exist in current tasks
    valid_tasks_df = df[df["id"].astype(str).isin([str(tid) for tid in selected_tasks])]
    
    if valid_tasks_df.empty:
        print("No valid tasks selected for update.")
        return {"tasks": df}
    
    # Second Phase : Get new status for selected tasks
    valid_task_corpus = print_update_message(valid_tasks_df)
    user_prompt = f"""
    User : {state.get("user_prev_message", "")}
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
    for update_info in updated_tasks_info:
        task_id = update_info.get("id")
        new_status = update_info.get("new_status")
        
        # Update the task status in the DataFrame
        df = update_task_status(df, task_id, new_status)
        print(f"Task ID {task_id} status updated to {new_status}.")
    
    state["tasks"] = df
    return state

def delete_tasks_node(state: TaskManagerState , run_llm_func) -> TaskManagerState:

    df = state["tasks"].copy()
    if df.empty:
        print("No tasks available to delete.")
        return {"tasks": df}
    
    print("Deleting tasks based on user input...")
    corpus = print_update_message(df, verbose=False)
    corpus_str = str(state.get("user_prev_message", "")) + "\n\nThis is a sheet of my tasks :\n\n" + "\n\n".join(corpus)
    response = run_llm_func(prompt=corpus_str, system_prompt=delete_task_prompt())
    response_json = parse_general_json_bracketed_string(response)
    selected_tasks = response_json.get("deleted_tasks", [])
    justification = response_json.get("justification", "")

    print("="*50)
    print(f"🧠 {justification}")
    print("="*50)

    for did in selected_tasks:# this can be done better using pandas filtering but we want to keep it simple and clear for now
        df = delete_task_by_id(df, did)
        print(f"Task ID {did} deleted.")

    return {"tasks": df}

def exit_node(state: TaskManagerState):
    return {"exit_requested": True}

def create_workflow(run_llm_func):
    workflow = StateGraph(TaskManagerState)

    # Add nodes
    # We use a lambda to pass the run_llm_func to the generate_tasks_node
    workflow.add_node("initial", lambda state: initial_node(state , run_llm_func))
    workflow.add_node("menu", lambda state: print_menu_node(state, run_llm_func))
    workflow.add_node("generate_tasks", lambda state: generate_tasks_node(state, run_llm_func))
    workflow.add_node("update_status", lambda state: update_status_node(state, run_llm_func))
    workflow.add_node("delete_tasks", lambda state: delete_tasks_node(state, run_llm_func))
    workflow.add_node("list_tasks", list_tasks_node)
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
    workflow.add_edge("exit", END)

    return workflow.compile()
