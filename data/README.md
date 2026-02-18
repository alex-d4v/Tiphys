# Data Storage (Data)

The `data/` directory contains persistence storage as CSV files.

## Content
- `tasks.csv`: Stores all tasks including their IDs, descriptions, dates, times, dependencies (as JSON strings), and current statuses.

## File Format
The task data is saved in CSV format and loaded at application startup to maintain context between sessions.
