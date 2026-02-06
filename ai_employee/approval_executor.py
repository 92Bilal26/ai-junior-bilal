"""Approval Executor

Watches /Approved folder and executes actions for approved items.
Handles different action types like email, payments, and attendance marking.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from ai_employee import config
from ai_employee.utils import (
    ensure_dir,
    log_line,
    parse_frontmatter,
    read_text,
    render_frontmatter,
    slugify,
    utc_now_iso,
    write_text,
)


def execute_attendance_marking(frontmatter: dict, body: str, log_path: Path) -> bool:
    """Execute ESS attendance marking."""
    try:
        date = frontmatter.get("date")
        if not date:
            from datetime import datetime

            date = datetime.now().strftime("%Y-%m-%d")

        log_line(log_path, f"Executing attendance marking for {date}")

        # Call the MCP server to mark attendance
        from mcp_servers.ess_attendance_mcp import handle_mark_attendance

        result = handle_mark_attendance({"date": date})

        if result.get("success"):
            log_line(log_path, f"✓ Attendance marked: {result.get('message')}")
            return True
        else:
            log_line(log_path, f"✗ Failed to mark attendance: {result.get('message')}")
            return False

    except Exception as e:
        log_line(log_path, f"ERROR marking attendance: {str(e)}")
        return False


def execute_email_action(frontmatter: dict, body: str, log_path: Path) -> bool:
    """Execute email sending action."""
    try:
        to = frontmatter.get("to", "")
        subject = frontmatter.get("subject", "")

        if not to:
            log_line(log_path, "ERROR: No 'to' email address in approval")
            return False

        log_line(log_path, f"Would send email to {to}: {subject}")
        # TODO: Integrate with MCP email server
        return True

    except Exception as e:
        log_line(log_path, f"ERROR executing email: {str(e)}")
        return False


def execute_approval_action(approval_path: Path, vault_path: Path) -> bool:
    """Execute action for approved item."""
    log_path = config.LOG_DIR / "approval_executor.log"
    ensure_dir(config.LOG_DIR)

    try:
        text = read_text(approval_path)
        fm, body = parse_frontmatter(text)
        action_type = fm.get("action", "").lower()
        task_type = fm.get("type", "").lower()

        log_line(log_path, f"Executing approved action: {approval_path.name} (type={task_type}, action={action_type})")

        # Execute based on type
        success = False
        if task_type == "attendance_marking":
            success = execute_attendance_marking(fm, body, log_path)
        elif task_type == "email" or action_type == "send_email":
            success = execute_email_action(fm, body, log_path)
        else:
            log_line(log_path, f"Unknown action type: {task_type}/{action_type}")
            return False

        # Move to Done folder
        if success:
            done_folder = vault_path / "Done"
            ensure_dir(done_folder)
            fm["executed_at"] = utc_now_iso()
            fm["status"] = "executed"
            content = render_frontmatter(fm, body)
            done_path = done_folder / approval_path.name
            write_text(done_path, content)
            approval_path.unlink()
            log_line(log_path, f"✓ Moved to Done: {done_path.name}")
            return True
        else:
            # Move to Rejected folder for manual review
            rejected_folder = vault_path / "Rejected"
            ensure_dir(rejected_folder)
            fm["failed_at"] = utc_now_iso()
            fm["status"] = "failed"
            content = render_frontmatter(fm, body)
            rejected_path = rejected_folder / approval_path.name
            write_text(rejected_path, content)
            approval_path.unlink()
            log_line(log_path, f"✗ Moved to Rejected: {rejected_path.name}")
            return False

    except Exception as e:
        log_line(log_path, f"ERROR processing approval {approval_path.name}: {str(e)}")
        return False


def process_approvals(vault_path: Path) -> int:
    """Find and execute all approved items."""
    approved_folder = vault_path / "Approved"
    if not approved_folder.exists():
        return 0

    count = 0
    for approval_path in sorted(approved_folder.glob("*.md")):
        if approval_path.name == ".gitkeep":
            continue
        if execute_approval_action(approval_path, vault_path):
            count += 1

    return count


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Approval executor")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval (seconds)")
    parser.add_argument("--vault", type=str, default=str(config.VAULT_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    vault_path = Path(args.vault).expanduser().resolve()

    if args.once:
        process_approvals(vault_path)
    else:
        import time

        while True:
            process_approvals(vault_path)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
