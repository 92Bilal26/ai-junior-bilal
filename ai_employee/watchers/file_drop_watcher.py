from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ai_employee import config
from ai_employee.utils import ensure_dir, load_json, log_line, save_json, slugify, utc_now_iso, write_text
from ai_employee.watchers.base import BaseWatcher


class FileDropWatcher(BaseWatcher):
    def __init__(self, drop_folder: Path, state_path: Path, check_interval: int = 30) -> None:
        super().__init__(check_interval=check_interval)
        self.drop_folder = drop_folder
        self.state_path = state_path
        self.log_path = config.LOG_DIR / "file_drop_watcher.log"

    def check(self) -> int:
        ensure_dir(self.drop_folder)
        state = load_json(self.state_path, default={"processed": {}})
        processed = state.get("processed", {})
        count = 0

        for file_path in sorted(self.drop_folder.glob("*")):
            if file_path.is_dir():
                continue
            key = str(file_path.resolve())
            mtime = file_path.stat().st_mtime
            if key in processed and processed[key] == mtime:
                continue

            inbox_target = self._copy_to_inbox(file_path)
            task_path = self._create_task(file_path, inbox_target)
            processed[key] = mtime
            count += 1
            log_line(self.log_path, f"Created task {task_path.name} for {file_path.name}")

        state["processed"] = processed
        save_json(self.state_path, state)
        return count

    def _copy_to_inbox(self, file_path: Path) -> Path:
        ensure_dir(config.VAULT_PATH / "Inbox")
        stem = slugify(file_path.stem)
        target = config.VAULT_PATH / "Inbox" / f"{stem}{file_path.suffix}"
        if target.exists():
            target = config.VAULT_PATH / "Inbox" / f"{stem}_{int(file_path.stat().st_mtime)}{file_path.suffix}"
        shutil.copy2(file_path, target)
        return target

    def _create_task(self, file_path: Path, inbox_target: Path) -> Path:
        ensure_dir(config.VAULT_PATH / "Needs_Action")
        stamp = utc_now_iso()
        slug = slugify(file_path.stem)
        task_name = f"FILE_{slug}_{stamp.replace(':', '').replace('.', '')}.md"
        task_path = config.VAULT_PATH / "Needs_Action" / task_name

        content = "\n".join(
            [
                "---",
                "type: file_drop",
                "source: drop_folder",
                "priority: normal",
                "status: new",
                f"created_at: {stamp}",
                f"original_name: {file_path.name}",
                f"inbox_copy: {inbox_target}",
                "---",
                "",
                "# File Drop",
                "A new file was dropped for processing.",
                "",
                "## Suggested Actions",
                "- [ ] Review file contents",
                "- [ ] Determine required updates",
                "- [ ] Request approval if needed",
                "",
            ]
        )
        write_text(task_path, content)
        return task_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="File drop watcher")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval (seconds)")
    parser.add_argument("--drop-folder", type=str, default=str(config.DROP_FOLDER))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    watcher = FileDropWatcher(
        drop_folder=Path(args.drop_folder).expanduser().resolve(),
        state_path=config.STATE_DIR / "file_drop_watcher.json",
        check_interval=args.interval,
    )
    if args.once:
        watcher.check()
    else:
        watcher.run()


if __name__ == "__main__":
    main()
