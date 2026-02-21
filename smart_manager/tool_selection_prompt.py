import datetime as dt
SELECT_ACTION_PROMPT = """
You are a helpful assistant designed to help users manage their tasks and goals effectively. Based on the user's input, you will determine the appropriate action to take.
Your task is to match user input to one of the following actions based on the content of the message. The actions are defined as follows:

- GM: The user is providing a General Message or update that doesn't fit into the other categories.
- L: The user wants to List all current tasks and their statuses.
- T: The user wants to input a new Task and have it broken down into actionable tasks.
- S: The user wants to edit the Status of an existing task, such as marking it as completed or updating its progress.
- M: The user wants to return to the main Menu or see the available options again.
- D: The user wants to Delete a task .
- C: The user wants to Comment on the recent tasks.
- Q: The user wants to Quit the application.

## Output Format
```json
{{
    "action": "T",
    "message": "User wants to input a new task and have it broken down into actionable tasks."
}}
```

## Response Factor:
- The `action` field must be one of the following: "T", "S", "L", "M", "GM", "D", "C", "Q".
- Only provide the JSON output as specified, no other text.
- Accompany the JSON output with a brief message acknowledging the user's input and the action taken, but ensure that the JSON is clearly distinguishable from the message.

"""

def select_action_prompt():
    return SELECT_ACTION_PROMPT

SELECT_SEARCH_TOOL_PROMPT = """
Today is : {today}.

You are a helpful assistant designed to help users manage their tasks and goals effectively.
The user has provided an input that requires you to search for relevant tasks using a set of tool .
Your task is to classify the user's input into one of the following search tools based on the content of the message and the user's intent:

The available search tools are:
{signatures}

## Output Format
```json
{{
    "selected_tools": [<tool_function_name> , ...],
    "justification": "The user's input contains a specific date, indicating that they want to search for tasks related to that date."
}}
```

## Response Factor:
- The `selected_tools` field should contain a list of `tool_function_name` strings from the available search tools above.
- The `justification` field should provide a brief explanation of why the selected tools were chosen based on the user's input.
- This is a multiclass classification task . It is probable that more than one tool is suitable to use based on the user's input .
- Only provide the JSON output as specified, no other text.
"""

def select_search_tool_prompt(signatures):
    today = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    return SELECT_SEARCH_TOOL_PROMPT.format(today=today, signatures="\n".join(signatures))

PARAMETRIZE_TOOL = """
Today is : {today}.
You are a task management expert. Your job is to extract parameters for a search tool from the user's input.

TOOL INFORMATION:
Name: {tool_name}
Signature: {signature}
Description: {description}

USER MESSAGE:
{user_input}

## Instructions:
1. Extract values for the parameters listed in the signature.
2. Return the parameters in a JSON object with a 'args' key.
3. If a parameter is a string, provide a string. Dates should be YYYY-MM-DD.
"""

def parametrize_tool_prompt(tool_info, user_input):
    today = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    return PARAMETRIZE_TOOL.format(
        today=today,
        tool_name=tool_info['name'],
        signature=tool_info['signature'],
        description=tool_info['description'],
        user_input=user_input
    )