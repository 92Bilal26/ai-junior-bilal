#!/usr/bin/env python3
"""
Execute Claude tasks by creating proper task specifications and invoking Claude Code.
This bypasses the CLI limitation by using Claude Code's actual task execution capabilities.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_employee import config
from ai_employee.utils import parse_frontmatter, read_text, write_text, log_line, utc_now_iso

LOG_PATH = config.VAULT_PATH / "Logs" / "task_executor.log"


def create_task_spec(task_path: Path, vault_path: Path) -> str:
    """Create a spec file for the task so Claude Code can execute it properly."""
    text = read_text(task_path)
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "")
    task_type = fm.get("type", "")
    instruction = body

    # Create a simple spec
    spec = f"""# Task: {title}

## Requirements
{instruction}

## Expected Output
- All files created in appropriate directory (apps/html/*, apps/python/*, etc.)
- Working, functional code
- Ready for use

## Success Criteria
- Files created
- Code is syntactically correct
- Application is functional
"""

    return spec


def get_execution_command(title: str, instruction: str) -> str:
    """Generate a proper execution command for Claude Code."""
    # For HTML apps, create a proper task
    if "html" in title.lower() and "app" in title.lower():
        app_name = title.split(":")[-1].strip().lower().replace(" ", "_")
        return f"""
Task: {title}

User instruction: {instruction}

Create the app with:
1. Create folder: apps/html/{app_name}/
2. Create index.html - complete HTML structure
3. Create styles.css - all CSS styling
4. Create app.js - all JavaScript functionality

Make it production-ready. Output full file contents.
"""

    return f"Complete this task: {title}\n\n{instruction}"


def get_task_description(task_path: Path) -> str:
    """Generate a description Claude Code can execute."""
    text = read_text(task_path)
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "")
    instruction = body.strip()

    # Return formatted instruction for Claude Code execution
    desc = f"""
You have been assigned this task:

TITLE: {title}

INSTRUCTIONS:
{instruction}

REQUIREMENTS:
1. Complete all requirements in the instruction above
2. For app scaffolding: Create complete, functional files
3. Create files in the appropriate apps/ directory
4. Files should be production-ready with proper formatting
5. When done, report completion status

Execute this task now.
"""
    return desc


def extract_app_info(title: str, instruction: str) -> tuple[str, str, str]:
    """Extract app language, name, and other info from task."""
    title_lower = title.lower()

    if "html" in title_lower:
        language = "html"
        app_name = title.split(":")[-1].strip().lower().replace(" ", "_")
    elif "python" in title_lower:
        language = "python"
        app_name = title.split(":")[-1].strip().lower().replace(" ", "_")
    elif "javascript" in title_lower or "js" in title_lower:
        language = "javascript"
        app_name = title.split(":")[-1].strip().lower().replace(" ", "_")
    elif "react" in title_lower:
        language = "react"
        app_name = title.split(":")[-1].strip().lower().replace(" ", "_")
    else:
        language = "unknown"
        app_name = "app"

    return language, app_name, instruction


def create_implementation_plan(task_path: Path, vault_path: Path) -> bool:
    """Create a proper implementation plan that Claude Code can execute."""
    text = read_text(task_path)
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "")
    task_type = fm.get("type", "")
    instruction = body.strip()

    if task_type != "claude_app":
        return False

    language, app_name, _ = extract_app_info(title, instruction)

    # Create a simple plan for Claude to execute
    plan = f"""# Plan: {title}

## What needs to be done
{instruction}

## Implementation steps
1. Create directory: apps/{language}/{app_name}/
2. Create all necessary files:
   - For HTML: index.html, styles.css, app.js
   - For Python: main.py, requirements.txt, README.md
   - For JavaScript: index.js, package.json, README.md
3. Make code production-ready
4. Test locally if possible

## Success criteria
- All files created
- Code compiles/runs without errors
- Meets the requirements above

## Next steps
- Claude Code should execute this directly
- Create files in the correct location
- Report completion
"""

    return True


def list_executable_tasks(vault_path: Path) -> list[Path]:
    """Find all tasks that need execution."""
    tasks = []
    needs_action = vault_path / "Needs_Action"

    if not needs_action.exists():
        return tasks

    for task_path in sorted(needs_action.glob("TASK_*.md")):
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)

        task_type = fm.get("type", "").lower()
        status = fm.get("status", "").lower()

        # Only get claude_app types that are planned or executing
        if task_type == "claude_app" and status in {"planned", "executing"}:
            tasks.append(task_path)

    return tasks


def show_task_info(task_path: Path) -> None:
    """Display task information for user to execute manually."""
    text = read_text(task_path)
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "")
    status = fm.get("status", "")
    instruction = body.strip()

    print(f"\n{'='*60}")
    print(f"Task: {title}")
    print(f"Status: {status}")
    print(f"File: {task_path.relative_to(config.VAULT_PATH)}")
    print(f"{'='*60}")
    print(f"\nInstruction:\n{instruction}")
    print(f"\n{'='*60}\n")


def main():
    print("Claude Task Executor - Direct Execution Guide\n")
    print("=" * 60)

    vault = config.VAULT_PATH
    tasks = list_executable_tasks(vault)

    if not tasks:
        print("No executable tasks found.")
        return

    print(f"Found {len(tasks)} executable task(s)\n")

    for i, task_path in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}]")
        show_task_info(task_path)

        text = read_text(task_path)
        fm, body = parse_frontmatter(text)
        title = fm.get("title", "")
        instruction = body.strip()

        language, app_name, _ = extract_app_info(title, instruction)

        print(f"Quick Execute Instructions:")
        print(f"1. Open Claude Code (interactive mode)")
        print(f"2. Enter this prompt:\n")
        print(f"Create an {language} app called '{app_name}'")
        print(f"Requirements: {instruction[:100]}...")
        print(f"Output location: apps/{language}/{app_name}/")
        print()

    print("\n" + "=" * 60)
    print("Alternative: Use Claude Code interactive with /sp.implement")
    print("Or invoke: claude < tasks-prompt.txt")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
