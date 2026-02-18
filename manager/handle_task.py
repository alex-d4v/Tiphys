import uuid
import datetime as dt
import pandas as pd
from const import STATUS_OPTIONS
from utils.parse_utils import parse_index_and_index_range_string
from utils.print_utils import print_update_message 

def update_task_status_by_index(df: pd.DataFrame) -> pd.DataFrame:
    """Interactively update the status of one or more tasks via a numbered menu."""
    if df.empty:
        print("No tasks to update.")
        return df
    
    print_update_message(df)
    
    try:
        choice = input("Select task number to update: ").strip()
        indeces = parse_index_and_index_range_string(choice)
        if not indeces:
            print("No valid task numbers selected.")
            return df
        
        for index in indeces:
            if index < 1 or index > len(df):
                print(f"Task number {index} is out of range.")
                continue
            
            # Use iloc for index-based access
            task_idx = index - 1
            current_status = df.iloc[task_idx]["status"]
            
            status_choice = input(f"Select new status number - {', '.join(f'[{i}] {status}' for i, status in enumerate(STATUS_OPTIONS, start=1))}: ").strip()
            try :
                status_index = int(status_choice)
                if status_index < 1 or status_index > len(STATUS_OPTIONS):
                    print("Invalid status number.")
                    continue
                new_status = STATUS_OPTIONS[status_index - 1]
                
                # Metadata update
                if new_status == "on work" and current_status != "on work":
                    df.iloc[task_idx, df.columns.get_loc("started_at")] = dt.datetime.now().isoformat()
                elif new_status == "done" and current_status != "done":
                    df.iloc[task_idx, df.columns.get_loc("ended_at")] = dt.datetime.now().isoformat()
                
                df.iloc[task_idx, df.columns.get_loc("status")] = new_status
            except ValueError:
                print("Invalid input for status. Please enter a number.")
                continue
    except (ValueError, IndexError):
        print("Invalid input.")
    except (EOFError, KeyboardInterrupt):
        print("\nUpdate cancelled.")

    return df

def update_task_status(df: pd.DataFrame, task_id: str, new_status: str) -> pd.DataFrame:
    """Update the status of a task by its ID in a DataFrame."""
    if new_status not in STATUS_OPTIONS:
        print(f"Invalid status: {new_status}. Status not updated.")
        return df
    
    # Use loc to update efficiently
    mask = df["id"].astype(str) == str(task_id)
    if not mask.any():
        return df
    
    # Get index of matching rows
    idx = df.index[mask]
    for i in idx:
        current_status = df.loc[i, "status"]
        
        # Metadata update
        if new_status == "on work" and current_status != "on work":
            df.loc[i, "started_at"] = dt.datetime.now().isoformat()
        elif new_status == "done" and current_status != "done":
            df.loc[i, "ended_at"] = dt.datetime.now().isoformat()
        
        df.loc[i, "status"] = new_status
        
    return df

def delete_task_by_id(df: pd.DataFrame, task_id: str) -> pd.DataFrame:
    """Delete a task by its ID from a DataFrame."""
    return df[df["id"].astype(str) != str(task_id)].reset_index(drop=True)