#!/bin/bash

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}    Ollama — Setup & Launch               ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}\n"

# ── Step 1: Check Ollama is installed ─────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Ollama not found. Installing...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ollama installation failed. Please install manually from https://ollama.com${NC}"
        exit 1
    fi
    echo -e "${GREEN}Ollama installed successfully.${NC}"
else
    echo -e "${GREEN}Ollama already installed: $(ollama --version)${NC}"
fi

# ── Step 2: Install Python dependency ─────────────────────────────────────────
echo -e "\n${YELLOW}[2/5] Installing Python dependencies...${NC}"
pip install openai --quiet
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install openai package. Check your Python/pip setup.${NC}"
    exit 1
fi
echo -e "${GREEN}Python dependencies ready.${NC}"

# ── Step 3: Start Ollama server ───────────────────────────────────────────────
echo -e "\n${YELLOW}[3/5] Starting Ollama server...${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}Ollama server is already running.${NC}"
else
    ollama serve &> /tmp/ollama.log &
    OLLAMA_PID=$!
    echo $OLLAMA_PID > /tmp/ollama.pid
    echo -e "${GREEN}Ollama server started (PID: $OLLAMA_PID).${NC}"
    # Give it a moment to initialise
    sleep 2
fi

# ── Step 4: Pull Qwen 7B if not already present ───────────────────────────────
echo -e "\n${YELLOW}[4/5] Checking for model...${NC}"
if ollama list | grep -q "qwen2.5:7b"; then
    echo -e "${GREEN}qwen2.5:7b already downloaded.${NC}"
else
    echo -e "${YELLOW}Downloading qwen2.5:7b (this may take a few minutes)...${NC}"
    ollama pull qwen2.5:7b
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to pull qwen2.5:7b. Check your internet connection.${NC}"
        exit 1
    fi
    echo -e "${GREEN}qwen2.5:7b downloaded successfully.${NC}"
fi

# ── Step 5: Run the app ───────────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/5] Launching local_llm.py...${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/local_llm.py"