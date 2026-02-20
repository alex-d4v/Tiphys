FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Environment variables (can be overridden by docker-compose)
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_BASE_URL=http://localhost:11434/v1
ENV MODEL_NAME=mistral:7b

# Default command
CMD ["python", "main.py"]