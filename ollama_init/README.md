# Ollama Server Initialization

Scripts to set up, start, and stop the local Ollama server running the **Qwen 2.5 7B** model.

## Contents
- `start.sh`: Installs Ollama if not present, pulls `qwen2.5:7b`, and launches the main application.
- `stop.sh`: Safely terminates the Ollama server and cleans up temporary log/PID files.

## Usage
To initialize and start:
```bash
./ollama_init/start.sh
```

To stop the background server:
```bash
./ollama_init/stop.sh
```

