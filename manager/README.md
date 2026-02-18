# Core Task Management (Manager)

The `manager/` directory contains the low-level logic for manipulating current tasks in the system.

## Components
- `handle_task.py`: Provides functions for updating task statuses and deleting tasks by ID or index.

## Features
- **Task Status Updating**: Change task states to "pending", "on work", "over deadline", or "done".
- **Task Deletion**: Remove tasks from the system while providing necessary feedback.
- **Interactive Updates**: Includes a command-line interface for selecting and updating multiple tasks at once.
