def collision_check_prompt(new_task_desc: str, relevant_tasks_str: str) -> str:
    return f"""
You are a task management consultant. Your job is to check if a new task (or set of tasks) being added is redundant or in conflict with existing tasks.

NEW TASK(S) TO ADD:
{new_task_desc}

EXISTING RELEVANT TASKS:
{relevant_tasks_str}

Evaluate if there are any "collisions":
1. Redundancy: Is the new task already covered by an existing one?
2. Conflict: Does the new task contradict or interfere with an existing one?
3. Dependency: Should the new task be a dependency rather than a new separate task?

Return your analysis in the following JSON format:
{{
    "collision_exists": bool,
    "justification": "Detailed explanation of why there is or isn't a collision. If a collision exists, explain specifically which tasks are involved.",
    "can_proceed": bool
}}

If "collision_exists" is true, "can_proceed" should usually be false, unless the collision is minor and can be ignored.
"""
