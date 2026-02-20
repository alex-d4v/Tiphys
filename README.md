# Task Manager with Local LLM (Qwen 2.5) & Neo4j

A state-of-the-art task management system that integrates local LLM capabilities with a graph database for persistent, intelligent task planning and execution. This project uses **Qwen 2.5 7B** via **Ollama** and a **Neo4j** graph to maintain complex dependencies and vector-based task searching.

## Features
- **Intelligent Task Generation**: Converts a high-level goal into a series of actionable subtasks with dependencies.
- **Natural Language Commands**: Manage, update, and delete tasks through a conversational interface powered by `langgraph`.
- **Vector-Based Retrieval**: Uses task embeddings to check for collisions, find relevant tasks during status updates, and perform semantic task deletion.
- **Temporal Search**: Retrieves tasks within a specific time radius (e.g., ±1 hour from now) for context-aware feedback (Comment Tasks).
- **Graph Database Persistence**: All tasks and relationships (DEPENDS_ON) are stored in Neo4j for persistent tracking.

## Directory Structure
- `db/`: Infrastructure for Neo4j via Docker.
- `neo4jmanager/`: Python interaction with the graph database.
- `manager/`: Core logic for task manipulation (status updating, deletion).
- `smart_manager/`: LLM-related logic, prompts, and the `langgraph` workflow state machine.
- `utils/`: Common utilities for CLI formatting and JSON parsing.
- `ollama_init/`: Scripts for setting up the local Ollama server and pulling models.

## Getting Started

### 1. Prerequisites
Ensure you have Docker and Python 3.10+ installed.

### 2. Setup Ollama
Install Ollama and start the local server:
```bash
./ollama_init/start.sh
```

### 3. Initialize Database
Setup the Neo4j environment and start the container:
```bash
./db/init.sh
```

### 4. Run the Application
```bash
# Set up .env if you haven't (init.sh handles this for you)
python3 main.py
```

## Advanced Interaction
The system uses **Vector Similarity Search** to ensure your tasks don't overlap (Collision Check) and to find relevant tasks even when descriptors aren't identical.

