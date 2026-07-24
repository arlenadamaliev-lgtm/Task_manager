import json
import os
import shutil
from datetime import datetime

from my_logger import log_action, log_error

TASKS_FILE = "tasks_log.jsonl"
BACKUP_FILE = "tasks_log.jsonl.bak"


def renumber_ids(task_list):
    """Renumbers task IDs from 1 to N (for use after deletion)."""
    for index, task in enumerate(task_list, start=1):
        task["id"] = index


def parse_target(target_str):
    """Converts a string to int if it's a number, otherwise returns as is."""
    return int(target_str) if target_str.isdigit() else target_str


def get_valid_deadline():
    """Prompts for a deadline, validates format, returns a string or None."""
    deadline = input("Enter deadline (YYYY-MM-DD) or Enter for no date: ").strip()
    if not deadline:
        return None
    try:
        datetime.strptime(deadline, "%Y-%m-%d")
        return deadline
    except ValueError:
        print("❌ Invalid date format. Deadline not set.")
        return None


def get_valid_priority():
    """Prompts for priority, returns 'medium' by default."""
    print("Available priorities: high (🔴), medium (🟡), low (🟢)")
    priority = input("Enter priority (Enter — medium): ").strip().lower()
    return priority if priority in ("high", "medium", "low") else "medium"


def load_tasks_from_file():
    """
    Loads tasks from a JSONL file.
    Returns a list of tasks (empty if the file doesn't exist or is empty).
    """
    tasks = []

    if not os.path.exists(TASKS_FILE):
        log_action("FILE_LOAD", "File not found, starting with empty list")
        return tasks

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    task = json.loads(line)
                    tasks.append(task)

        log_action("FILE_LOAD", f"Loaded {len(tasks)} tasks from {TASKS_FILE}")

        renumber_ids(tasks)
        log_action("FILE_LOAD", f"IDs renumbered: now {len(tasks)} tasks")

    except json.JSONDecodeError as e:
        log_error("FILE_LOAD", f"JSON parsing error on line {line_num}: {e}")
        print(f"❌ File read error: {e}")
    except Exception as e:
        log_error("FILE_LOAD", f"Unknown error: {e}")
        print(f"❌ Failed to load file: {e}")

    return tasks


def append_task_to_file(task):
    """
    Adds a single task to the end of the JSONL file.
    task: task dictionary
    """
    mode = "a" if os.path.exists(TASKS_FILE) else "w"
    with open(TASKS_FILE, mode, encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")
    log_action("FILE_APPEND", f"Added task ID: {task.get('id')}")


def rewrite_all_tasks_to_file(task_list):
    """
    Overwrites the entire file with the current task list.
    Creates a backup before overwriting.
    task_list: list of task dictionaries
    """
    if os.path.exists(TASKS_FILE):
        shutil.copy2(TASKS_FILE, BACKUP_FILE)
        log_action("FILE_BACKUP", f"Backup created: {BACKUP_FILE}")

    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        for task in task_list:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    log_action("FILE_REWRITE", f"Rewritten {len(task_list)} tasks")


def sort_by_priority(task_list):
    """Returns a new task list sorted by priority (high → medium → low → no priority)."""
    priority_order = {"high": 1, "medium": 2, "low": 3}
    return sorted(
        task_list,
        key=lambda task: priority_order.get(task.get("priority", ""), 4),
    )


def get_current_datetime():
    """Returns the current date and time in YYYY-MM-DD HH:MM:SS format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_overdue_tasks(task_list):
    """
    Checks all tasks: if a deadline is set and is before the current date,
    and the status is not "done", changes the status to "overdue".
    """
    today = datetime.now().date()
    for task in task_list:
        if task.get("deadline") and task["status"] != "done":
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            if deadline_date < today:
                task["status"] = "overdue"
                log_action(
                    "AUTO_OVERDUE",
                    f"ID: {task['id']}, text: {task['text']}, deadline: {task['deadline']}",
                )


def delete_task(task_list, task_id_or_text):
    """
    Deletes a task by ID (int) or exact text match (str).
    Returns:
        - (True, "message") if successful
        - (False, "message") if error
    """
    for index, task in enumerate(task_list):
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            log_action("DELETE_TASK", f"ID: {task['id']}, text: {task['text']}")
            del task_list[index]
            renumber_ids(task_list)
            rewrite_all_tasks_to_file(task_list)
            return True, f"Task '{task['text']}' deleted."

    log_error("DELETE_TASK", f"Task with ID/text '{task_id_or_text}' not found")
    return False, f"Task with ID/text '{task_id_or_text}' not found."


def update_status(task_list, task_id_or_text, new_status):
    """
    Updates the status of a task by ID (int) or exact text match (str).
    new_status: "pending", "done", "overdue"
    Returns:
        - (True, "message") if successful
        - (False, "message") if error
    """
    if new_status not in ("pending", "done", "overdue"):
        return (
            False,
            f"Invalid status: {new_status}. Allowed: pending, done, overdue",
        )

    for task in task_list:
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            old_status = task["status"]
            task["status"] = new_status
            log_action(
                "UPDATE_STATUS",
                f"ID: {task['id']}, text: {task['text']}, status: {old_status} → {new_status}",
            )
            rewrite_all_tasks_to_file(task_list)
            return (
                True,
                f"Status of task '{task['text']}' changed from '{old_status}' to '{new_status}'.",
            )
    log_error("UPDATE_STATUS", f"Task with ID/text '{task_id_or_text}' not found")
    return False, f"Task with ID/text '{task_id_or_text}' not found."


def edit_task_text(task_list, task_id_or_text, new_text):
    """
    Changes the text of a task by ID (int) or exact text match (str).
    Updates the creation date when editing.
    Returns:
        - (True, old_text, new_text, "message") if successful
        - (False, "message") if error
    """
    if not new_text or new_text.strip() == "":
        log_error("EDIT_TASK", "New task text is empty")
        return False, "New task text cannot be empty."
    if new_text.isdigit():
        log_error("EDIT_TASK", "New task text consists only of digits")
        return False, "Task text cannot be only numeric."

    for task in task_list:
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            old_text = task["text"]
            task["text"] = new_text.strip()
            task["created"] = get_current_datetime()
            log_action(
                "EDIT_TASK",
                f"ID: {task['id']}, old text: '{old_text}', new text: '{new_text.strip()}'",
            )
            rewrite_all_tasks_to_file(task_list)
            return (
                True,
                old_text,
                new_text.strip(),
                f"Task text changed from '{old_text}' to '{new_text.strip()}' (date updated).",
            )
    log_error("EDIT_TASK", f"Task with ID/text '{task_id_or_text}' not found")
    return False, f"Task with ID/text '{task_id_or_text}' not found."


def add_task(task_list, text, priority, deadline=None):
    """
    Adds a new task.
    Returns:
        - (True, task_id, "message") if successful
        - (False, "message") if error
    """
    if not text:
        log_error("ADD_TASK", "Task text is empty")
        return False, "Task text cannot be empty."

    if text.isdigit():
        log_error("ADD_TASK", "Task text is a number")
        return False, "Task text cannot be only numeric."
    if priority not in ("high", "medium", "low"):
        print(f"Invalid priority: {priority}. Allowed: high, medium, low")
        priority = "medium"

    task_id = len(task_list) + 1
    task = {
        "id": task_id,
        "text": text,
        "status": "pending",
        "created": get_current_datetime(),
        "priority": priority,
    }

    if deadline:
        task["deadline"] = deadline

    task_list.append(task)
    log_action(
        "ADD_TASK",
        f"ID: {task_id}, text: {text.strip()}, priority: {priority}, deadline: {deadline}",
    )
    append_task_to_file(task)
    return True, task_id, f"Task added: {text} (ID: {task_id})"


def show_tasks(task_list):
    """Shows all tasks with their status"""
    if not task_list:
        print("\n📭 Task list is empty.")
        return

    check_overdue_tasks(task_list)
    task_list[:] = sort_by_priority(task_list)
    rewrite_all_tasks_to_file(task_list)
    print("Task list sorted by priority:")

    for task in task_list:
        status_icon = (
            "✓"
            if task["status"] == "done"
            else ("⚓ " if task["status"] == "overdue" else "◻")
        )

        deadline_info = ""
        if task.get("deadline"):
            deadline_info = f", deadline: {task['deadline']}"

        print(
            f"{status_icon} {task['id']}. {task['text']} (created: {task['created']}) {deadline_info}"
        )
    return


def main():

    tasks = load_tasks_from_file()

    while True:
        print("\n--- TASK MANAGER ---")
        print("1. Add task")
        print("2. Show all tasks")
        print("3. Delete task")
        print("4. Change status (pending/done/overdue)")
        print("5. Edit task text")
        print("0. Exit")

        choice = input("Select action (0-5): ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        elif choice == "1":
            text = input("Enter task text: ").strip()
            deadline = get_valid_deadline()
            priority = get_valid_priority()

            result = add_task(tasks, text, priority, deadline)
            print(f"✅ {result[2]}" if result[0] else f"❌ {result[1]}")  # type: ignore

        elif choice == "2":
            show_tasks(tasks)

        elif choice == "3":
            target = parse_target(
                input("Enter number or text of task to delete: ").strip()
            )
            success, msg = delete_task(tasks, target)
            print(f"🗑️ {msg}" if success else f"❌ {msg}")

        elif choice == "4":
            target = parse_target(input("Enter number or text of task: ").strip())
            new_status = (
                input("Enter new status (pending/done/overdue): ").strip().lower()
            )
            success, msg = update_status(tasks, target, new_status)
            print(f"✅ {msg}" if success else f"❌ {msg}")

        elif choice == "5":
            target = parse_target(
                input("Enter number or current text of task: ").strip()
            )
            new_text = input("Enter new task text: ").strip()
            result = edit_task_text(tasks, target, new_text)
            if result[0]:
                print(f"✅ {result[3]}")  # type: ignore
            else:
                print(f"❌ {result[1]}")

        else:
            print("Error: enter a number from 0 to 5.")


if __name__ == "__main__":
    main()
