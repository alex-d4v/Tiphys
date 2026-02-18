# Utility Module (Utils)

Standard formatting and parsing functions used across the task manager.

## Components
- `parse_utils.py`: Extracts and validates JSON from LLM responses, handle task id generation, and provides string parsing for actions.
- `print_utils.py`: Beautifully formats tasks into tables and displays status updates with icons.

## Features
- **JSON Extraction**: Robust regex-based extraction to separate LLM narrative from structured JSON.
- **Table View**: Clear, formatted table displaying task IDs, descriptions, dates, times, dependencies, and statuses.
- **Status Icons**: Visual indicators for various task states (pending, on work, over deadline, done).
