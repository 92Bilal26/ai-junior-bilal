#!/usr/bin/env python3
"""Test script to verify the auto-execution workflow."""

from pathlib import Path
import sys

# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_employee import config
from ai_employee.claude_task_executor import (
    find_executable_tasks,
    get_task_instruction,
    is_claude_task,
    is_planned_task,
)
from ai_employee.utils import parse_frontmatter, read_text

def test_task_discovery():
    """Test that we can discover planned Claude tasks."""
    print("=== Testing Task Discovery ===")
    vault = config.VAULT_PATH
    tasks = find_executable_tasks(vault)

    if tasks:
        print(f"Found {len(tasks)} executable task(s):")
        for task_path, fm, body in tasks:
            print(f"  - {task_path.name}")
            print(f"    Type: {fm.get('type')}")
            print(f"    Status: {fm.get('status')}")
            print(f"    Title: {fm.get('title')}")
    else:
        print("No executable tasks found (expected if no planned tasks exist)")
    return len(tasks)

def test_task_properties():
    """Test task property detection."""
    print("\n=== Testing Task Properties ===")
    vault = config.VAULT_PATH
    needs_action = vault / "Needs_Action"

    if not needs_action.exists():
        print("Needs_Action folder not found")
        return

    for task_path in sorted(needs_action.glob("TASK_*.md"))[:3]:  # Test first 3 tasks
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)

        print(f"\nTask: {task_path.name}")
        print(f"  Type: {fm.get('type')}")
        print(f"  Status: {fm.get('status')}")
        print(f"  Is Claude task: {is_claude_task(fm)}")
        print(f"  Is planned: {is_planned_task(fm)}")
        print(f"  Would execute: {is_claude_task(fm) and is_planned_task(fm)}")

        if is_claude_task(fm):
            instruction = get_task_instruction(fm, body)
            print(f"  Instruction: {instruction[:100]}...")

def test_workflow_status():
    """Display workflow status."""
    print("\n=== Workflow Status ===")
    vault = config.VAULT_PATH

    # Count tasks by folder
    folders = {
        "Needs_Action": vault / "Needs_Action",
        "Plans": vault / "Plans",
        "Pending_Approval": vault / "Pending_Approval",
        "Done": vault / "Done",
    }

    for folder_name, folder_path in folders.items():
        if folder_path.exists():
            count = len(list(folder_path.glob("*.md")))
            print(f"  {folder_name}: {count} file(s)")
        else:
            print(f"  {folder_name}: 0 file(s) (folder doesn't exist)")

    # Count executable tasks
    executable = find_executable_tasks(vault)
    print(f"\n  Executable (planned + Claude type): {len(executable)}")

def main():
    print("Testing Auto-Execution Workflow\n")

    task_count = test_task_discovery()
    test_task_properties()
    test_workflow_status()

    print("\n=== Test Complete ===")
    if task_count > 0:
        print("[OK] Found executable tasks ready for auto-execution")
    else:
        print("[INFO] No executable tasks found")
        print("  To test: Create a task via dashboard with type 'claude_app'")
        print("  Then orchestrator will plan it")
        print("  Then executor will automatically execute it")

if __name__ == "__main__":
    main()
