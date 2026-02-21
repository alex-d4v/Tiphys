import pandas as pd
import datetime as dt

STATUS_ICONS = {
    "pending":       "○  pending",
    "on work":       "◑  on work",
    "over deadline": "⊗  over deadline",
    "done":          "●  done",
}

def task_order(df: pd.DataFrame) -> pd.DataFrame:
    priority_map = {"high": 1, "medium": 2, "low": 3}
    
    if df.empty:
        return df

    # Create temporary sort keys
    df_copy = df.copy()
    
    df_copy["date_sort"] = df_copy["date"].fillna("9999-12-31").astype(str)
    df_copy["time_sort"] = df_copy["time"].fillna("23:59").astype(str)
    
    # Handle priority mapping safely
    def get_prio_val(p):
        p_str = str(p).lower() if p and not pd.isna(p) else "medium"
        return priority_map.get(p_str, 2)
        
    df_copy["prio_sort"] = df_copy["priority"].apply(get_prio_val)
    
    df_sorted = df_copy.sort_values(by=["date_sort", "time_sort", "prio_sort"]).drop(columns=["date_sort", "time_sort", "prio_sort"])
    
    return df_sorted

def print_update_message(tasks: pd.DataFrame, verbose: bool = True) -> list[str]:
    title_line = "\n>>> SELECT TASKS <<<\n" + "-"*75
    corpus = [title_line] 
    
    if verbose:
        print(title_line)
    
    # Handle list input for backward compatibility during transition or if passed from unpack_tasks
    if isinstance(tasks, list):
        tasks_list = tasks
    else:
        tasks_list = tasks.to_dict(orient="records")

    for i, task in enumerate(tasks_list):
        task_id = task["id"]
        prio = str(task.get("priority", "medium")).upper()
        desc_clean = str(task.get("description", "")).replace('\n', ' ')
        short_desc = desc_clean if len(desc_clean) <= 45 else desc_clean[:42] + "..."
        current_icon = STATUS_ICONS.get(task.get("status", "pending"), "(P)")
        
        if verbose:
            print(f"  ({i+1:<2}) [{prio:<6}] {short_desc:<45} {current_icon}")
            
        corpus_entry = f"ID: {task_id} | Priority: {prio} | Description: {desc_clean} | Status: {task.get('status', 'pending')} | Dependencies: {task.get('dependencies', [])} | Blocked Tasks: {task.get('blocked_tasks', [])}"
        corpus.append(corpus_entry)
        
    if verbose:
        print("-" * 75)
        print("  (0)  CANCEL")
        print("-" * 75)
    
    corpus.append("  [0] Cancel")
    return corpus

# ── Table printer ──────────────────────────────────────────────────────────────
def print_tasks_table(tasks: pd.DataFrame) -> None:
    import textwrap
    
    if tasks.empty:
        print("No tasks to display.")
        return
        
    # Simple ASCII widths
    COL_ID     = 8
    COL_PRIO   = 6
    COL_DESC   = 40
    COL_DATE   = 10
    COL_TIME   = 5
    COL_DEP    = 15
    COL_BLOCKS = 15
    COL_STATUS = 12

    cols = [COL_ID, COL_PRIO, COL_DESC, COL_DATE, COL_TIME, COL_DEP, COL_BLOCKS, COL_STATUS]
    
    # Plain ASCII Borders
    sep = "+" + "+".join("-" * (c + 2) for c in cols) + "+"
    head_sep = "+" + "+".join("=" * (c + 2) for c in cols) + "+"

    print(f"\n{head_sep}")
    headers = ["ID", "PRIO", "DESCRIPTION", "DATE", "TIME", "DEPS", "BLOCKS", "STATUS"]
    header_row = "| " + " | ".join(f"{h:<{c}}" for h, c in zip(headers, cols)) + " |"
    print(header_row)
    print(head_sep)

    sorted_tasks = task_order(tasks)
    for _, task in sorted_tasks.iterrows():
        task_id  = str(task["id"])[:COL_ID]
        prio     = str(task.get("priority", "med")).upper()[:COL_PRIO]
        desc     = str(task.get("description", ""))
        date     = str(task.get("date", "N/A"))
        time     = str(task.get("time", "--:--"))
        status   = str(task.get("status", "pending"))
        
        # Simple status text
        status_text = status.upper()[:COL_STATUS]
        
        desc_lines = textwrap.wrap(desc, COL_DESC)
        
        dep_ids = task.get("dependencies", [])
        dep_str = ", ".join(str(d)[:6] for d in dep_ids) if isinstance(dep_ids, list) and dep_ids else "-"
        dep_lines = textwrap.wrap(dep_str, COL_DEP)
        
        block_ids = task.get("blocked_tasks", [])
        block_str = ", ".join(str(b)[:6] for b in block_ids) if isinstance(block_ids, list) and block_ids else "-"
        block_lines = textwrap.wrap(block_str, COL_BLOCKS)
        
        max_lines = max(len(desc_lines), len(dep_lines), len(block_lines), 1)
        # Ensure at least one line per task
        while len(desc_lines) < max_lines: desc_lines.append("")
        while len(dep_lines) < max_lines: dep_lines.append("")
        while len(block_lines) < max_lines: block_lines.append("")

        for i in range(max_lines):
            id_val   = task_id if i == 0 else ""
            pr_val   = prio if i == 0 else ""
            dt_val   = date if i == 0 else ""
            tm_val   = time if i == 0 else ""
            st_val   = status_text if i == 0 else ""
            
            row = "| " + " | ".join([
                f"{id_val:<{COL_ID}}",
                f"{pr_val:<{COL_PRIO}}",
                f"{desc_lines[i]:<{COL_DESC}}",
                f"{dt_val:<{COL_DATE}}",
                f"{tm_val:<{COL_TIME}}",
                f"{dep_lines[i]:<{COL_DEP}}",
                f"{block_lines[i]:<{COL_BLOCKS}}",
                f"{st_val:<{COL_STATUS}}"
            ]) + " |"
            print(row)
        print(sep)
    return None

def print_tasks_table_today(tasks: pd.DataFrame) -> None :
    today = dt.datetime.now().strftime("%Y-%m-%d")
    today_tasks = tasks[tasks["date"] == today]
    if today_tasks.empty:
        print("No tasks scheduled for today.")
        return None
    else:
        print_tasks_table(today_tasks)