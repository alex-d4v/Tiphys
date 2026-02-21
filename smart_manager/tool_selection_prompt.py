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

You are a helpful assistant on selecting tools for exploring and searching for relevant tasks .
You act as an interface between the user and the database .
You are given a set of retrieval tools that can be used to explore the database .
The user has provided an input that requires you to search for relevant tasks using this set of tools .
You are trying to check whether this specific input can be matched to any of the available tasks in the database .
Your task is to classify the user's input into a set of tool-s based on the following available search tools . 
You have to match the user's input to one or more of the tools that can be effectively used to find relevant tasks in the database .

The available search tools are:
{signatures}

## Output Format
```json
{{
    "selected_tools": [<tool_function_name> , ...],
    "justification": "<justification_of_tool_selection>"
}}
```

## Response Factor:
- The `selected_tools` field should contain a list of `tool_function_name` strings from the available search tools above.
- At least one tool should be selected . It is possible that more than one tool is suitable to use based on the user's input . Select them all .
- The `justification` field should provide the specification of the tool on the use case .
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

## Output Format
```json
{{
    "args": {{
        <param_name>: <param_value>,
        ...
    }},
    "justification": "<a brief explanation of how the parameters were extracted from the user's input>"
}}
```

## Response Factor:
- The `args` field should contain a dictionary of parameter names and their corresponding values extracted from the user's input. The parameter names should match those in the tool's signature.
- The `justification` field should provide a brief explanation of how the parameters were extracted from the user's input, including any relevant context or reasoning.
- Only provide the JSON output as specified, no other text.
"""

def parametrize_tool_prompt(tool_info):
    today = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    return PARAMETRIZE_TOOL.format(
        today=today,
        tool_name=tool_info['name'],
        signature=tool_info['signature'],
        description=tool_info['description'],
    )