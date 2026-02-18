#!/bin/bash

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}══════════════════════════════════════════${NC}"
echo -e "${YELLOW}      Mistral 7B + Ollama — Shutdown      ${NC}"
echo -e "${YELLOW}══════════════════════════════════════════${NC}\n"

STOPPED=0

# ── Method 1: Kill via saved PID file ─────────────────────────────────────────
if [ -f /tmp/ollama.pid ]; then
    PID=$(cat /tmp/ollama.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping Ollama server (PID: $PID)...${NC}"
        kill "$PID"
        sleep 1
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID"
            echo -e "${YELLOW}Force-killed PID $PID.${NC}"
        fi
        STOPPED=1
    fi
    rm -f /tmp/ollama.pid
fi

# ── Method 2: Kill any remaining ollama processes ─────────────────────────────
REMAINING=$(pgrep -x "ollama")
if [ -n "$REMAINING" ]; then
    echo -e "${YELLOW}Stopping remaining Ollama processes...${NC}"
    pkill -x "ollama"
    sleep 1
    # Force kill if still hanging
    if pgrep -x "ollama" > /dev/null; then
        pkill -9 -x "ollama"
        echo -e "${YELLOW}Force-killed remaining Ollama processes.${NC}"
    fi
    STOPPED=1
fi

# ── Clean up log file ─────────────────────────────────────────────────────────
if [ -f /tmp/ollama.log ]; then
    rm -f /tmp/ollama.log
    echo -e "${GREEN}Cleaned up log file.${NC}"
fi

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}✔ Ollama server stopped successfully.${NC}"
else
    echo -e "${GREEN}✔ No running Ollama server found — nothing to stop.${NC}"
fi

echo -e "\n${YELLOW}══════════════════════════════════════════${NC}"
echo -e "${YELLOW}              Shutdown complete           ${NC}"
echo -e "${YELLOW}══════════════════════════════════════════${NC}"