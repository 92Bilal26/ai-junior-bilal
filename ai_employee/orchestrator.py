from __future__ import annotations

import argparse
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


APPROVAL_TYPES = {"email", "whatsapp", "git", "git_push", "payment", "social"}


def needs_plan(frontmatter: dict) -> bool:
    status = frontmatter.get("status", "").lower()
    return status not in {"planned", "done"}


def requires_approval(frontmatter: dict) -> bool:
    raw = frontmatter.get("requires_approval", "").lower()
    if raw in {"true", "yes", "1"}:
        return True
    task_type = frontmatter.get("type", "").lower()
    return task_type in APPROVAL_TYPES


def infer_title(frontmatter: dict, body: str, fallback: str) -> str:
    if "title" in frontmatter:
        return frontmatter["title"]
    for line in body.splitlines():
        if line.strip().startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def plan_steps(task_type: str) -> list[str]:
    base = [
        "Understand request and constraints",
        "Gather required context/files",
        "Draft output or changes",
        "Request approval if required",
        "Execute approved action",
        "Log outcome and mark task done",
    ]
    specific = {
        "email": ["Draft reply in Pending_Approval", "Send after approval"],
        "whatsapp": ["Draft response in Pending_Approval", "Send after approval"],
        "git": ["Create commit locally", "Push after approval"],
        "git_push": ["Create commit locally", "Push after approval"],
        "file_drop": ["Review dropped file", "Summarize requested changes"],
        "doc_update": ["Update Word/Excel file", "Save with versioned name"],
    }
    return base + specific.get(task_type, [])


def create_plan(task_path: Path, frontmatter: dict, body: str, vault_path: Path) -> Path:
    ensure_dir(vault_path / "Plans")
    task_type = frontmatter.get("type", "task")
    title = infer_title(frontmatter, body, task_path.stem)
    stamp = utc_now_iso()
    slug = slugify(title)
    plan_path = vault_path / "Plans" / f"PLAN_{slug}_{stamp.replace(':', '').replace('.', '')}.md"
    approval_needed = requires_approval(frontmatter)

    steps = plan_steps(task_type)
    checklist = "\n".join(f"- [ ] {step}" for step in steps)
    content = "\n".join(
        [
            "---",
            "type: plan",
            f"source_task: {task_path}",
            f"created_at: {stamp}",
            f"requires_approval: {'true' if approval_needed else 'false'}",
            "---",
            "",
            f"# Plan: {title}",
            "",
            "## Checklist",
            checklist,
            "",
        ]
    )
    write_text(plan_path, content)
    return plan_path


def update_task_status(task_path: Path, frontmatter: dict, body: str, plan_path: Path) -> None:
    frontmatter["status"] = "planned"
    frontmatter["planned_at"] = utc_now_iso()
    frontmatter["plan_file"] = str(plan_path)
    content = render_frontmatter(frontmatter, body)
    write_text(task_path, content)


def process_tasks(vault_path: Path) -> int:
    needs_action = vault_path / "Needs_Action"
    ensure_dir(needs_action)
    ensure_dir(config.LOG_DIR)
    log_path = config.LOG_DIR / "orchestrator.log"

    count = 0
    for task_path in sorted(needs_action.glob("*.md")):
        if task_path.name == ".gitkeep":
            continue
        text = read_text(task_path)
        fm, body = parse_frontmatter(text)
        if not needs_plan(fm):
            continue
        plan_path = create_plan(task_path, fm, body, vault_path)
        update_task_status(task_path, fm, body, plan_path)
        log_line(log_path, f"Planned {task_path.name} -> {plan_path.name}")
        count += 1
    return count


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI employee orchestrator")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval (seconds)")
    parser.add_argument("--vault", type=str, default=str(config.VAULT_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    vault_path = Path(args.vault).expanduser().resolve()

    if args.once:
        process_tasks(vault_path)
    else:
        while True:
            process_tasks(vault_path)
            import time

            time.sleep(args.interval)


if __name__ == "__main__":
    main()
