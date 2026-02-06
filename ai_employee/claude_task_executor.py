from __future__ import annotations

import re
from pathlib import Path

from ai_employee import config
from ai_employee.utils import (
    ensure_dir,
    log_line,
    parse_frontmatter,
    read_text,
    render_frontmatter,
    utc_now_iso,
    write_text,
)


CLAUDE_TASK_TYPES = {"claude_app", "claude_task", "claude_code"}
LOG_PATH = config.VAULT_PATH / "Logs" / "task_executor.log"


def get_task_instruction(frontmatter: dict, body: str) -> str:
    """Extract the instruction for Claude from task body."""
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## Instruction"):
            # Get everything after the "## Instruction" header
            instruction_lines = []
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    break
                instruction_lines.append(lines[j])
            return "\n".join(instruction_lines).strip()
    # Fallback: use body as instruction
    return body.strip()


def is_claude_task(frontmatter: dict) -> bool:
    """Check if task is meant for Claude execution."""
    task_type = frontmatter.get("type", "").lower()
    return task_type in CLAUDE_TASK_TYPES


def is_planned_task(frontmatter: dict) -> bool:
    """Check if task has been planned."""
    status = frontmatter.get("status", "").lower()
    return status == "planned"


def extract_output_from_response(task_type: str, instruction: str) -> str:
    """
    Extract expected output format from instruction.
    Returns a string describing what Claude should produce.
    """
    if "calculator" in instruction.lower():
        return "HTML files in apps/html/calculator/ (index.html, styles.css, app.js)"
    if "landing page" in instruction.lower():
        return "HTML files in apps/html/landing_page/ (index.html, styles.css, app.js)"
    if task_type == "claude_app":
        # Extract app name from instruction
        match = re.search(r'apps/\w+/(\w+)', instruction)
        if match:
            app_name = match.group(1)
            return f"App scaffolded in apps/*/{ app_name}/"
    return "Task completed by Claude"


def mark_task_executing(task_path: Path, frontmatter: dict, body: str) -> None:
    """Update task status to 'executing'."""
    frontmatter["status"] = "executing"
    frontmatter["executing_at"] = utc_now_iso()
    content = render_frontmatter(frontmatter, body)
    write_text(task_path, content)


def mark_task_done(task_path: Path, frontmatter: dict, body: str, output: str = "") -> Path:
    """Move task to Done folder and update status."""
    done_folder = config.VAULT_PATH / "Done"
    ensure_dir(done_folder)

    frontmatter["status"] = "done"
    frontmatter["completed_at"] = utc_now_iso()
    if output:
        frontmatter["output"] = output

    content = render_frontmatter(frontmatter, body)
    destination = done_folder / task_path.name
    write_text(destination, content)

    # Remove original file
    task_path.unlink(missing_ok=True)
    return destination


def is_executing_task(frontmatter: dict) -> bool:
    """Check if task is currently executing."""
    status = frontmatter.get("status", "").lower()
    return status == "executing"


def should_timeout(frontmatter: dict, timeout_minutes: int = 10) -> bool:
    """
    Check if task has been executing too long and should timeout.
    Default: 10 minutes.
    """
    if not is_executing_task(frontmatter):
        return False

    executing_at = frontmatter.get("executing_at", "")
    if not executing_at:
        return True  # No timestamp, consider it stuck

    try:
        from datetime import datetime, timezone, timedelta
        exec_time = datetime.fromisoformat(executing_at.replace("+00:00", "+00:00"))
        now = datetime.now(timezone.utc)
        elapsed = (now - exec_time).total_seconds() / 60  # Convert to minutes
        return elapsed > timeout_minutes
    except Exception:
        return True


def find_executable_tasks(vault_path: Path) -> list[tuple[Path, dict, str]]:
    """
    Find planned Claude tasks ready for execution.
    Returns list of (task_path, frontmatter, body) tuples.
    """
    tasks = []
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return tasks

    for task_path in sorted(needs_action.glob("TASK_*.md")):
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)

        # Only execute Claude task types that are planned
        if is_claude_task(fm) and is_planned_task(fm):
            tasks.append((task_path, fm, body))

    return tasks


def find_stuck_tasks(vault_path: Path, timeout_minutes: int = 10) -> list[tuple[Path, dict, str]]:
    """
    Find executing tasks that have timed out.
    Returns list of (task_path, frontmatter, body) tuples.
    """
    tasks = []
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return tasks

    for task_path in sorted(needs_action.glob("TASK_*.md")):
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)

        # Find Claude tasks that are stuck executing
        if is_claude_task(fm) and should_timeout(fm, timeout_minutes):
            tasks.append((task_path, fm, body))

    return tasks


def execute_task(task_path: Path, frontmatter: dict, body: str, send_prompt_fn) -> bool:
    """
    Execute a Claude task by sending it to Claude.
    Returns True if execution was sent successfully.
    """
    try:
        # Mark as executing
        mark_task_executing(task_path, frontmatter, body)

        # Get instruction
        instruction = get_task_instruction(frontmatter, body)
        task_type = frontmatter.get("type", "")
        title = frontmatter.get("title", task_path.stem)

        # Build execution prompt for Claude with detailed instructions
        prompt = f"""You must complete this task. Be direct and thorough.

TASK: {title}
TYPE: {task_type}

INSTRUCTION: {instruction}

REQUIREMENTS:
- Create the app folder and all files in the correct location
- For HTML apps: Create in apps/html/{{app_name}}/
- Files needed: index.html, styles.css, app.js (minimum)
- Each file should be complete and functional
- Do not ask for confirmation, just create the files
- Output complete file contents when creating files

START EXECUTION NOW:"""

        # Send to Claude
        result = send_prompt_fn(prompt)

        if result.get("ok"):
            log_line(LOG_PATH, f"Executing task: {task_path.name}")
            return True
        else:
            log_line(LOG_PATH, f"Failed to send task to Claude: {result.get('error')}")
            # Revert status back to planned
            frontmatter["status"] = "planned"
            frontmatter.pop("executing_at", None)
            content = render_frontmatter(frontmatter, body)
            write_text(task_path, content)
            return False

    except Exception as e:
        log_line(LOG_PATH, f"Error executing task {task_path.name}: {str(e)}")
        return False


def extract_app_name(title: str, instruction: str) -> str:
    """Extract the app name from task title or instruction."""
    # Try to extract from title like "Scaffold html app: blog_page"
    if ":" in title:
        return title.split(":")[-1].strip().lower().replace(" ", "_")
    # Try to extract from instruction paths
    for pattern in ["apps/html/", "apps/backend/", "apps/frontend/"]:
        if pattern in instruction:
            parts = instruction.split(pattern)
            if len(parts) > 1:
                app_name = parts[1].split("/")[0].strip()
                return app_name
    return ""


def check_and_complete_task(task_path: Path, vault_path: Path) -> bool:
    """
    Check if a task's output exists and move it to Done.
    Returns True if task was completed.
    """
    text = read_text(task_path)
    fm, body = parse_frontmatter(text)

    # Check if output files exist for this task
    task_type = fm.get("type", "")
    title = fm.get("title", "")
    instruction = get_task_instruction(fm, body)

    # For claude_app tasks, check if the app folder was created
    if task_type == "claude_app":
        app_name = extract_app_name(title, instruction)
        if app_name:
            # Check for app in different language folders
            apps_folder = vault_path.parent / "apps"
            for lang_folder in ["html", "backend", "frontend", "python", "javascript", "react"]:
                app_path = apps_folder / lang_folder / app_name
                if app_path.exists() and list(app_path.glob("*")):
                    # Found app folder with content - mark as done
                    output = f"App created: apps/{lang_folder}/{app_name}/"
                    mark_task_done(task_path, fm, body, output)
                    log_line(LOG_PATH, f"Completed task: {task_path.name} (output detected: {output})")
                    return True

    return False


def cleanup_stuck_tasks(vault_path: Path) -> int:
    """
    Find and move stuck tasks to Done folder.
    Tasks are considered stuck if they've been executing > 10 minutes.
    Returns count of tasks moved to Done.
    """
    stuck = find_stuck_tasks(vault_path, timeout_minutes=10)
    count = 0

    for task_path, frontmatter, body in stuck:
        try:
            # Try to detect if output was created
            if check_and_complete_task(task_path, vault_path):
                count += 1
                continue

            # If no output, move to Done anyway (manual action needed)
            output = "Executor timeout - manual review needed"
            mark_task_done(task_path, frontmatter, body, output)
            log_line(LOG_PATH, f"Moved stuck task to Done: {task_path.name}")
            count += 1
        except Exception as e:
            log_line(LOG_PATH, f"Error handling stuck task {task_path.name}: {str(e)}")

    return count


def process_executable_tasks(vault_path: Path, send_prompt_fn) -> int:
    """
    Find and execute all planned Claude tasks.
    Also cleans up stuck executing tasks.
    Returns count of tasks processed.
    """
    ensure_dir(config.LOG_DIR)
    count = 0

    # First, try to complete any stuck tasks
    count += cleanup_stuck_tasks(vault_path)

    # Then execute newly planned tasks
    tasks = find_executable_tasks(vault_path)
    for task_path, frontmatter, body in tasks:
        if execute_task(task_path, frontmatter, body, send_prompt_fn):
            count += 1

    return count
