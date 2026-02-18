import datetime as dt

STATUS_ICONS = {
    "pending":       "○  pending",
    "on work":       "◑  on work",
    "over deadline": "⊗  over deadline",
    "done":          "●  done",
}

def print_update_message(tasks: list , verbose : bool = True) -> list[str]:
    title_line = "\n>>> SELECT TASKS <<<\n" + "-"*75
    corpus = [title_line] 
    
    if verbose:
        print(title_line)
    
    for i, task in enumerate(tasks):
        task_id = task["id"]
        prio = task.get("priority", "medium").upper()
        desc_clean = task["description"].replace('\n', ' ')
        short_desc = desc_clean if len(desc_clean) <= 45 else desc_clean[:42] + "..."
        current_icon = STATUS_ICONS.get(task.get("status", "pending"), "(P)")
        
        if verbose:
            print(f"  ({i+1:<2}) [{prio:<6}] {short_desc:<45} {current_icon}")
            
        corpus_entry = f"Index: {i+1} | ID: {task_id} | Priority: {prio} | Description: {desc_clean} | Status: {task.get('status', 'pending')}"
        corpus.append(corpus_entry)
        
    if verbose:
        print("-" * 75)
        print("  (0)  CANCEL")
        print("-" * 75)
    
    corpus.append("  [0] Cancel")
    return corpus

# ── Table printer ──────────────────────────────────────────────────────────────
def print_tasks_table(tasks: list) -> None:
    import textwrap
    
    # Simple ASCII widths
    COL_ID     = 8
    COL_PRIO   = 6
    COL_DESC   = 40
    COL_DATE   = 10
    COL_TIME   = 5
    COL_DEP    = 15
    COL_STATUS = 12

    cols = [COL_ID, COL_PRIO, COL_DESC, COL_DATE, COL_TIME, COL_DEP, COL_STATUS]
    
    # Plain ASCII Borders
    sep = "+" + "+".join("-" * (c + 2) for c in cols) + "+"
    head_sep = "+" + "+".join("=" * (c + 2) for c in cols) + "+"

    print(f"\n{head_sep}")
    headers = ["ID", "PRIO", "DESCRIPTION", "DATE", "TIME", "DEPS", "STATUS"]
    header_row = "| " + " | ".join(f"{h:<{c}}" for h, c in zip(headers, cols)) + " |"
    print(header_row)
    print(head_sep)

    for task in tasks:
        task_id  = str(task["id"])[:COL_ID]
        prio     = str(task.get("priority", "med")).upper()[:COL_PRIO]
        desc     = task.get("description", "")
        date     = task.get("date", "N/A")
        time     = task.get("time", "--:--")
        status   = task.get("status", "pending")
        
        # Simple status text if icons cause rendering issues
        status_text = status.upper()[:COL_STATUS]
        
        desc_lines = textwrap.wrap(desc, COL_DESC)
        dep_ids = task.get("dependencies", [])
        dep_str = ", ".join(str(d)[:6] for d in dep_ids) if dep_ids else "-"
        dep_lines = textwrap.wrap(dep_str, COL_DEP)
        
        max_lines = max(len(desc_lines), len(dep_lines), 1)
        desc_lines += [""] * (max_lines - len(desc_lines))
        dep_lines  += [""] * (max_lines - len(dep_lines))

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
                f"{st_val:<{COL_STATUS}}"
            ]) + " |"
            print(row)
        print(sep)

def print_tasks_table_today(tasks: list) -> None :
    today = dt.datetime.now().strftime("%Y-%m-%d")
    today_tasks = [task for task in tasks if task["date"] == today]
    if not today_tasks:
        print("No tasks scheduled for today.")
        return None
    else:
        print_tasks_table(today_tasks)