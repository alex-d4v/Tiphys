# Ollama Server Initialization

Scripts to set up, start, and stop the local Ollama server running the Mistral 7B model.

## Contents
- `start.sh`: Installs Ollama if not present, installs Python dependencies, pulls `mistral:7b`, and launches the application.
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
