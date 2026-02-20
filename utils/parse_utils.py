import json
import uuid
import re

def parse_action_string(s: str) -> str:
    """Parse a user input string to determine the intended action."""
    s = s.strip().lower()
    if s in ['t', 'task', 'tasks']:
        return 'generate_tasks'
    elif s in ['s', 'status', 'update']:
        return 'update_status'
    elif s in ['q', 'quit', 'exit']:
        return 'exit'
    elif s in ['m', 'menu']:
        return 'menu'
    elif s in ['gm', 'general message']:
        return 'general_message'
    elif s in ['l', 'list']:
        return 'list_tasks'
    elif s in ['d', 'delete']:
        return 'delete_tasks'
    elif s in ['c', 'comment']:
        return 'comment_tasks'
    else:
        return 'unknown'

def parse_index_and_index_range_string(s: str) -> list[int]:
    """Parse a string containing numbers and ranges into a list of integers."""
    indices = set()
    parts   = re.split(r'[,\s]+', s.strip())
    for part in parts:
        if '-' in part:
            start, end = part.split('-')
            indices.update(range(int(start), int(end) + 1))
        else:
            indices.add(int(part))
    return sorted(indices)

def input_task(max_tries: int = 3) -> str | None:
    """Prompt the user for a task, with retry logic."""
    for attempt in range(1, max_tries + 1):
        try:
            task = input("Enter the task you want to perform: ").strip()
            if task:
                return task
            print("Task cannot be empty. Please try again.")
        except (EOFError, KeyboardInterrupt):
            print("\nInput interrupted.")
            break
        except Exception as e:
            print(f"An error occurred (attempt {attempt}/{max_tries}): {e}")
    return None

def _extract_json(s: str) -> str:
    """Extract a JSON string from a fenced code block or find the first/last braces."""
    # Match from ```json to the next ```
    match = re.search(r"```json\s*(.*?)\n?```", s, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Try without json tag
    match = re.search(r"```\s*(.*?)\n?```", s, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Normalize escaped braces {{ }} -> { }
    normalized = s.replace("{{", "{").replace("}}", "}")

    # Try to find the first { ... } block in the normalized string
    json_start = normalized.find("{")
    json_end = normalized.rfind("}")
    if json_start != -1 and json_end != -1 and json_start < json_end:
        json_str = normalized[json_start:json_end + 1]
        try:
            json.loads(json_str)
            return json_str.strip()
        except json.JSONDecodeError:
            pass

    print("No valid JSON found in the string.")
    print(f"String content was:\n{s}")
    return ""

def parse_general_json_bracketed_string(s: str) -> dict:
    try:
        json_str = _extract_json(s)
        if not json_str:
            print("No JSON found in the string.")
            return {}
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return {}
    except Exception as e:
        print(f"An error occurred while parsing JSON: {e}")
        return {}

def unpack_tasks(response: str) -> list[dict]:
    try:
        json_str = _extract_json(response)
        if not json_str:
            print("No JSON found in the response.")
            return []
        
        data     = json.loads(json_str)
        tasks    = data.get("tasks", [])

        for task in tasks:
            task["id"] = str(uuid.uuid4())
            # Initialize analysis fields
            task["priority"] = task.get("priority", "medium")
            task["status"] = "pending"
            task["started_at"] = None
            task["ended_at"] = None

        for task in tasks:
            temp_dependencies = []
            for d in task.get("dependencies", []):
                try:
                    dep_idx = int(d) - 1
                    if 0 <= dep_idx < len(tasks):
                        temp_dependencies.append(tasks[dep_idx]["id"])
                except (ValueError, TypeError, IndexError):
                    continue
            task["dependencies"] = temp_dependencies
            task["status"] = "pending"

        return tasks
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return []
    except Exception as e:
        print(f"An error occurred while unpacking tasks: {e}")
        return []
