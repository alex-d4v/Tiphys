# Smart Manager with LLM and Graph Automation

The `smart_manager/` module contains the intelligent workflow state machine and its corresponding prompts. It uses `langgraph` to manage conversation state, routing, and complex task transitions.

## Workflow Nodes (`workflow.py`)
- `initial`: Handles welcome messages and initial setup.
- `menu`: Directs the user to choose their next action.
- `generate_tasks`: Uses LLM to create structured subtasks.
- `update_status`: Employs vector similarity to find and update relevant tasks.
- `delete_tasks`: Performs semantic searches to remove one or more tasks safely.
- `comment_tasks`: Provides context-aware feedback (e.g. ±1 hour from current time).
- `list_tasks`: Retrieves all tasks from the graph for full visibility.

## Prompts Layer
- `collision_prompt.py`: Logic to ensure new tasks don't overlap with existing ones using LLM reasoning.
- `general_prompts.py`: Welcome messages, overall conversation, and "Comment Tasks" responses.
- `task_gen_prompt.py`: Logic for breaking down complex desires into actionable JSON-structured tasks.
- `tool_selection_prompt.py`: Maps natural language user intent to workflow actions.
- `task_sched_prompt.py`: Specialized logic for date/time extraction.

## Vector Search Integration
Each node can now leverage the `neo4jmanager` to perform similarity searches based on task embeddings. These embeddings are generated during the workflow using the same model that powers the conversation (Qwen 2.5).
