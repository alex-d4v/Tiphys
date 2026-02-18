import datetime as dt

STATUS_ICONS = {
    "pending":       "○  pending",
    "on work":       "◑  on work",
    "over deadline": "⊗  over deadline",
    "done":          "●  done",
}

def print_update_message(tasks: list , verbose : bool = True) -> list[str]:
    corpus =["\n── Update Task Status ─────────────────────────────",] 
    
    if verbose:
        print(corpus[0])
    for i, task in enumerate(tasks):
        id = task["id"]
        title = task["title"] if task.get("title") else f"Task {task['id']}"
        desc_text = "".join(line + '\n' for line in task["description"].splitlines())
        short_desc = desc_text if len(desc_text) <= 50 else desc_text[:47] + "..."
        current    = STATUS_ICONS.get(task.get("status", "pending"), "○  pending")
        if verbose:
            print(f"  [{i+1}] {short_desc:<53} {current}")
        # the same string to corpus for LLM understanding
        corpus.append(f" Title : {title} | ID : {id} | Description : {desc_text} | Status : {current}")
    if verbose:
        print("───────────────────────────────────────────────────")
    corpus.append("  [0] Cancel")
    return corpus

# ── Table printer ──────────────────────────────────────────────────────────────
def print_tasks_table(tasks: list) -> None:
    import textwrap
    COL_ID     = 10
    COL_DESC   = 55
    COL_DATE   = 12
    COL_TIME   = 10
    COL_DEP    = 30
    COL_STATUS = 16

    border_top = f"┌{'─'*(COL_ID+2)}┬{'─'*(COL_DESC+2)}┬{'─'*(COL_DATE+2)}┬{'─'*(COL_TIME+2)}┬{'─'*(COL_DEP+2)}┬{'─'*(COL_STATUS+2)}┐"
    border_mid = f"├{'─'*(COL_ID+2)}┼{'─'*(COL_DESC+2)}┼{'─'*(COL_DATE+2)}┼{'─'*(COL_TIME+2)}┼{'─'*(COL_DEP+2)}┼{'─'*(COL_STATUS+2)}┤"
    border_bot = f"└{'─'*(COL_ID+2)}┴{'─'*(COL_DESC+2)}┴{'─'*(COL_DATE+2)}┴{'─'*(COL_TIME+2)}┴{'─'*(COL_DEP+2)}┴{'─'*(COL_STATUS+2)}┘"

    print(f"\n{border_top}")
    print(f"│ {'ID':<{COL_ID}} │ {'Description':<{COL_DESC}} │ {'Date':<{COL_DATE}} │ {'Time':<{COL_TIME}} │ {'Dependencies':<{COL_DEP}} │ {'Status':<{COL_STATUS}} │")
    print(border_mid)

    for task in tasks:
        task_id    = str(task["id"])[:COL_ID]
        dep_str    = ", ".join(str(d)[:COL_ID] for d in task["dependencies"]) if task["dependencies"] else "None"
        dep_lines  = textwrap.wrap(dep_str, COL_DEP)
        desc_lines = textwrap.wrap(task["description"], COL_DESC)
        status     = STATUS_ICONS.get(task.get("status", "pending"), "○  pending")

        max_lines  = max(len(desc_lines), len(dep_lines), 1)
        desc_lines += [""] * (max_lines - len(desc_lines))
        dep_lines  += [""] * (max_lines - len(dep_lines))

        for j, (desc_line, dep_line) in enumerate(zip(desc_lines, dep_lines)):
            id_cell    = task_id if j == 0 else ""
            date       = task["date"] if j == 0 else ""
            time       = task["time"] if j == 0 else ""
            status_col = status if j == 0 else ""
            print(f"│ {id_cell:<{COL_ID}} │ {desc_line:<{COL_DESC}} │ {date:<{COL_DATE}} │ {time:<{COL_TIME}} │ {dep_line:<{COL_DEP}} │ {status_col:<{COL_STATUS}} │")

        print(border_mid)

    print(f"\033[A{border_bot}")

def print_tasks_table_today(tasks: list) -> None :
    today = dt.datetime.now().strftime("%Y-%m-%d")
    today_tasks = [task for task in tasks if task["date"] == today]
    if not today_tasks:
        print("No tasks scheduled for today.")
        return None
    else:
        print_tasks_table(today_tasks)