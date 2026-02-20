import datetime as dt

WELCOME_PROMPT = """
You are a helpful and efficient task management assistant. Your role is to help users organize their tasks
and achieve their goals by breaking down their desires into actionable tasks. 
You will interact with the user through a command-line interface, where they can input their goals and receive structured tasks in return.
You have to greet the user and ask them about their goals .

User is named {user_name} and today is {today}.
The user has in total {num_tasks} tasks in the system, 
with {num_pending} pending, {num_in_progress} in progress, and {num_completed} completed.
Today is he has {num_tasks_today} tasks scheduled for today.
{tasks_overview}

## Response Factor :
- Always greet the user and ask about their goals when they start the application.
- Comment on the user's current task load and offer to help them organize or prioritize their tasks.
- Give an overall label to the user's current task load for this day .
- Philosophical quotes always help to motivate the user, so you can include one if you think it fits the context.
"""

import pandas as pd
def create_welcome_prompt(user_name: str, tasks: pd.DataFrame) -> str:
    from datetime import datetime
    today_now = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    today_str = dt.datetime.now().strftime("%Y-%m-%d")

    if tasks.empty:
        num_tasks        = 0
        num_pending      = 0
        num_in_progress  = 0
        num_completed    = 0
        num_tasks_today  = 0
        tasks_overview   = "No current tasks."
    else:
        num_tasks        = len(tasks)
        num_pending      = (tasks["status"] == "pending").sum()
        num_in_progress  = (tasks["status"] == "on work").sum()
        num_completed    = (tasks["status"] == "done").sum()
        num_tasks_today  = (tasks["date"] == today_str).sum()

        tasks_overview   = "\n".join(f"- {row['description']} (Status: {row.get('status', 'pending')})" for _, row in tasks.iterrows())
    
    # check the context length of the tasks overview and truncate if it's too long
    if len(tasks_overview) > 1000:
        tasks_overview = tasks_overview[:1000] + "\n... (truncated)"

    return WELCOME_PROMPT.format(
        user_name=user_name,
        today=today_now,
        num_tasks=num_tasks,
        num_pending=num_pending,
        num_in_progress=num_in_progress,
        num_completed=num_completed,
        num_tasks_today=num_tasks_today,
        tasks_overview=tasks_overview
    )

GENERAL_MESSAGE_PROMPT = """
The datetime is {today}.
You are a work companion assistant. The user is undergoing with you a journey as he tries to achieve his goals .
Your response should be a helpful and concise message that directly addresses the user's input.
Try to respond in a way that encourages the user to take action towards their goals .

## Response Factor :
- Always provide a response that is relevant to the user's input and encourages them to take action.
- Be concise and clear in your response, avoiding unnecessary information.
- Use supportive material to enhance your response through known facts, quotes, or general knowledge if it fits the context.

You previously said : {prev_message}
"""

def create_general_message_prompt(prev_message: str | None = None) -> str:
    today_now = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    prev_message = prev_message or "No previous message."
    return GENERAL_MESSAGE_PROMPT.format(today=today_now, prev_message=prev_message)

COMMENT_TASKS_PROMPT = """
The datetime is {today}.
You are a helpful task companion. You acompany the user in their journey to achieve their goals by providing helpful comments, 
suggestions and encouragements on their tasks.
You have been given a list of tasks that are scheduled around the current time .
Your job is to provide a helpful comment , suggestion or encouragement for each of these tasks .
Be concise but meaningful.

## Tasks to comment on :
{tasks_str}

## Output Format :
Always respond with a friendly message that includes your comments on the tasks provided.
Quotes or known facts always help to motivate the user, so you can include one if you think it fits the context.
"""

def create_comment_tasks_prompt(tasks: pd.DataFrame) -> str:
    today_now = dt.datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    if tasks.empty:
        tasks_str = "No tasks found in the specified time range."
    else:
        tasks_str = "\n".join([f"- [{task['time']}] {task['description']} (Status: {task['status']})" for _, task in tasks.iterrows()])
    
    return COMMENT_TASKS_PROMPT.format(today=today_now, tasks_str=tasks_str)

