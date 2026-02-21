def collision_check_prompt(planned_tasks_str: str, relevant_tasks_str: str) -> str:
    return f"""
You are a task management consultant. Your job is to check if a new task (or set of tasks) being added is redundant or in conflict with existing tasks.

NEW TASKS FOR CREATION:
{planned_tasks_str}

EXISTING RELEVANT TASKS:
{relevant_tasks_str}

Compare these and evaluate if there are any "collisions":
1. Redundancy: Is the new task already covered by an existing one? (Exact same goal and time)
2. Conflict: Does the new task contradict or interfere with an existing one? (Same time slot, different goal)
3. Dependency: Should the new task be a dependency rather than a new separate task?

Return your analysis in the following JSON format:
{{
    "collision_exists": bool,
    "collision_type": "<Redundancy|Conflict|Dependency|None>",
    "justification": "Detailed explanation of why there is or isn't a collision. If a collision exists, explain specifically which tasks are involved. Use task IDs if available.",
    "can_proceed": bool
}}

Only and only iff the collision_type is "Redundancy" , flag can_proceed as false , otherwise , flag can_proceed as true.
"""
