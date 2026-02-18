# Task Manager with LLM (Mistral 7B)

A sophisticated task management system that leverages local LLM capabilities via Ollama and `langgraph` to provide an interactive, intelligent task planning and tracking experience.

## Features
- **Intelligent Task Generation**: Break down goals into actionable subtasks with dependencies.
- **Natural Language Interaction**: Manage tasks through conversational commands.
- **Workflow Automation**: Uses `langgraph` to manage state transitions and complex tool selections.
- **Local LLM Integration**: Uses Mistral 7B running locally via Ollama.

## Directory Structure
- `manager/`: Core task manipulation logic (delete, update).
- `smart_manager/`: LLM-related logic, prompts, and the `langgraph` workflow.
- `utils/`: Common utilities for parsing and printing.
- `ollama_init/`: Scripts to set up and manage the local Ollama server.
- `data/`: Persistent storage for tasks.

## Getting Started
To start the application, ensure Ollama is installed and the Mistral 7B model is pulled. You can use the scripts in `ollama_init/` for setup.

```bash
python3 main.py
```
