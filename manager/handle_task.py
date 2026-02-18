import uuid
from const import STATUS_OPTIONS
from utils.parse_utils import parse_index_and_index_range_string
from utils.print_utils import print_update_message 

def update_task_status_by_index(tasks: list) -> list:
    """Interactively update the status of a task via a numbered menu."""
    if not tasks:
        print("No tasks to update.")
        return tasks
    
    print_update_message(tasks)
    
    try:
        choice = input("Select task number to update: ").strip()
        indeces = parse_index_and_index_range_string(choice)
        if not indeces:
            print("No valid task numbers selected.")
            return tasks
        
        for index in indeces:
            if index < 1 or index > len(tasks):
                print(f"Task number {index} is out of range.")
                continue
            
            task = tasks[index - 1]            
            status_choice = input(f"Select new status number - {', '.join(f'[{i}] {status}' for i, status in enumerate(STATUS_OPTIONS, start=1))}: ").strip()
            try :
                status_index = int(status_choice)
                if status_index < 1 or status_index > len(STATUS_OPTIONS):
                    print("Invalid status number.")
                    continue
                task["status"] = STATUS_OPTIONS[status_index - 1]
            except ValueError:
                print("Invalid input for status. Please enter a number.")
                continue
    except (ValueError, IndexError):
        print("Invalid input.")
    except (EOFError, KeyboardInterrupt):
        print("\nUpdate cancelled.")

    return tasks

def update_task_status(current_tasks: list , task_id : uuid.UUID , new_status : str) -> list:
    """Update the status of a task by its ID."""
    if new_status not in STATUS_OPTIONS:
        print(f"Invalid status: {new_status}. Status not updated.")
        return current_tasks
    
    for task in current_tasks:
        if task["id"] == task_id:
            task["status"] = new_status
            break
    return current_tasks

def delete_task_by_id(current_tasks: list , task_id : uuid.UUID) -> list:
    """Delete a task by its ID."""
    return [task for task in current_tasks if task["id"] != task_id]