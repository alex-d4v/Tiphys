# Smart Manager with LLM and Graph Automation

The `smart_manager/` module contains the intelligent workflow and its corresponding prompts. It uses `langgraph` to manage the conversation state and task transitions.

## Key Components
- `workflow.py`: Defines the state machine that routes user input to the correct action node (menu, generate, update, delete, exit).
- **Prompts Layer**:
    - `general_prompts.py`: Welcome and overall conversational responses.
    - `task_gen_prompt.py`: Logic for breaking down desires into actionable tasks.
    - `task_sched_prompt.py`: Scheduling logic (if implemented).
    - `tool_selection_prompt.py`: Routes user intent to the correct task action.

## LLM Interaction
Each node in the workflow invokes the Mistral 7B model using Ollama to interpret user needs and generate structured JSON responses that the system can process automatically.
