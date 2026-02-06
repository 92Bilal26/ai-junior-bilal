#!/usr/bin/env python3
"""Complete Claude tasks that have output files created."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_employee import config
from ai_employee.claude_task_executor import (
    find_stuck_tasks,
    check_and_complete_task,
    is_executing_task,
)
from ai_employee.utils import parse_frontmatter, read_text, log_line

LOG_PATH = config.VAULT_PATH / "Logs" / "task_completion.log"


def complete_executing_tasks():
    """Find executing tasks with output files and complete them."""
    vault = config.VAULT_PATH
    needs_action = vault / "Needs_Action"

    if not needs_action.exists():
        print("No Needs_Action folder found")
        return 0

    completed = 0
    for task_path in sorted(needs_action.glob("TASK_*.md")):
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)

        # Only check executing Claude tasks
        if is_executing_task(fm):
            print(f"\nChecking: {task_path.name}")
            print(f"  Status: {fm.get('status')}")
            print(f"  Type: {fm.get('type')}")

            # Try to complete if output exists
            if check_and_complete_task(task_path, vault):
                print(f"  Result: COMPLETED")
                completed += 1
            else:
                print(f"  Result: Still executing / no output yet")

    return completed


def main():
    print("=== Complete Executing Claude Tasks ===\n")

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    completed = complete_executing_tasks()

    print(f"\n=== Summary ===")
    print(f"Completed: {completed} task(s)")

    if completed > 0:
        log_line(LOG_PATH, f"Completed {completed} executing task(s)")


if __name__ == "__main__":
    main()
