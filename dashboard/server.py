from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import urlparse

DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
sys.path.insert(0, str(REPO_ROOT))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

from ai_employee import config  # noqa: E402
from ai_employee.orchestrator import process_tasks  # noqa: E402
from ai_employee.claude_runner import ensure_running as ensure_claude  # noqa: E402
from ai_employee.claude_runner import send_prompt as send_claude_prompt  # noqa: E402
from ai_employee.claude_runner import start as start_claude  # noqa: E402
from ai_employee.claude_runner import status as status_claude  # noqa: E402
from ai_employee.claude_runner import stop as stop_claude  # noqa: E402
from ai_employee.claude_task_executor import process_executable_tasks  # noqa: E402
from ai_employee.utils import ensure_dir, log_line, parse_frontmatter, slugify, utc_now_iso, write_text  # noqa: E402

VAULT = config.VAULT_PATH
LOG_PATH = VAULT / "Logs" / "dashboard.log"
QUEUE_SIGNAL = VAULT / "Signals" / "claude_queue.md"


def json_response(handler: SimpleHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json_body(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def ensure_inside_vault(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
        if VAULT in resolved.parents or resolved == VAULT:
            return resolved
    except FileNotFoundError:
        return None
    return None


def list_tasks(folder: Path) -> list[dict]:
    items: list[dict] = []
    if not folder.exists():
        return items
    for path in sorted(folder.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        title = fm.get("title", "")
        if not title:
            for line in body.splitlines():
                if line.strip().startswith("#"):
                    title = line.lstrip("#").strip()
                    break
        if not title:
            title = path.stem.replace("_", " ")
        items.append(
            {
                "id": path.stem,
                "title": title,
                "type": fm.get("type", "task"),
                "status": fm.get("status", ""),
                "path": str(path.relative_to(VAULT)),
            }
        )
    return items


def tail_lines(path: Path, limit: int = 60) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-limit:]


def move_item(rel_path: str, target_folder: Path) -> tuple[bool, str]:
    source = VAULT / rel_path
    resolved = ensure_inside_vault(source)
    if not resolved or not resolved.exists():
        return False, "invalid path"
    target_folder.mkdir(parents=True, exist_ok=True)
    destination = target_folder / resolved.name
    resolved.replace(destination)
    return True, str(destination.relative_to(VAULT))


def create_task(title: str, body: str, task_type: str = "task") -> str:
    needs_action = VAULT / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    stamp = utc_now_iso()
    slug = slugify(title)
    filename = f"TASK_{slug}_{stamp.replace(':', '').replace('.', '')}.md"
    path = needs_action / filename
    content = "\n".join(
        [
            "---",
            f"type: {task_type}",
            "source: dashboard",
            "priority: normal",
            "status: new",
            f"created_at: {stamp}",
            f"title: {title}",
            "---",
            "",
            f"# {title}",
            "",
            body.strip() if body else "Task created from dashboard.",
            "",
        ]
    )
    write_text(path, content)
    return str(path.relative_to(VAULT))


def create_claude_app_task(language: str, name: str, instruction: str) -> str:
    title = f"Scaffold {language} app: {name}"
    body_lines = [
        "## Instruction for Claude",
        instruction.strip() if instruction else "Scaffold the app using the preferred CLI for this framework.",
        "",
        "## Expected Output",
        f"- Create folder under apps/{slugify(language)}/{slugify(name)}",
        "- Run the appropriate framework CLI to scaffold the project",
        "- Document any dependencies or next steps in the vault",
    ]
    return create_task(title, "\n".join(body_lines), task_type="claude_app")


def update_queue_signal(task_path: str, instruction: str) -> None:
    ensure_dir(QUEUE_SIGNAL.parent)
    content = "\n".join(
        [
            "# Claude Task Queue",
            "",
            f"Last queued task: {task_path}",
            "",
            "## Instruction",
            instruction.strip() if instruction else "Read the task file and create a plan. Do not execute without approval.",
            "",
        ]
    )
    write_text(QUEUE_SIGNAL, content)
    log_line(LOG_PATH, f"Queue signal updated for {task_path}")


def notify_claude(task_path: str) -> None:
    autoload = os.getenv("CLAUDE_AUTOLOAD", "false").lower() in {"1", "true", "yes"}
    if not autoload:
        return
    ensure_claude()
    prompt = f"New task queued. Please read {QUEUE_SIGNAL} and plan only; wait for approval before actions."
    result = send_claude_prompt(prompt)
    if not result.get("ok"):
        log_line(LOG_PATH, f"Failed to send Claude prompt: {result.get('error')}")


def run_create_app(language: str, name: str, command: str | None, allow_command: bool) -> dict:
    safe_language = slugify(language)
    safe_name = slugify(name)
    if not safe_language or not safe_name:
        return {"ok": False, "error": "Invalid language or name."}

    script_path = REPO_ROOT / "scripts" / "create-app.ps1"
    if not script_path.exists():
        return {"ok": False, "error": "create-app.ps1 not found."}

    args = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-Language",
        safe_language,
        "-Name",
        safe_name,
    ]

    if command:
        allow_env = os.getenv("DASHBOARD_ALLOW_COMMANDS", "false").lower() in {"1", "true", "yes"}
        if not allow_command or not allow_env:
            return {
                "ok": False,
                "error": "Command execution disabled. Set DASHBOARD_ALLOW_COMMANDS=true and check allow box.",
            }
        args.extend(["-Command", command])

    result = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    log_line(LOG_PATH, f"create-app {safe_language}/{safe_name} exit={result.returncode}")
    if result.stdout:
        log_line(LOG_PATH, result.stdout.strip())
    if result.stderr:
        log_line(LOG_PATH, result.stderr.strip())

    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip() or "create-app failed"}

    return {
        "ok": True,
        "language": safe_language,
        "name": safe_name,
        "path": f"apps/{safe_language}/{safe_name}",
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_post(parsed.path)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown route")

    def handle_api_get(self, path: str) -> None:
        if path == "/api/summary":
            tasks = list_tasks(VAULT / "Needs_Action")
            approvals = list_tasks(VAULT / "Pending_Approval")
            claude_state = status_claude()
            payload = {
                "tasks_open": len(tasks),
                "approvals_open": len(approvals),
                "watchers": 1,
                "last_sync": utc_now_iso(),
                "claude_running": bool(claude_state.get("running")),
            }
            return json_response(self, payload)
        if path == "/api/tasks":
            return json_response(self, {"items": list_tasks(VAULT / "Needs_Action")})
        if path == "/api/approvals":
            return json_response(self, {"items": list_tasks(VAULT / "Pending_Approval")})
        if path == "/api/logs":
            logs = []
            logs.extend(tail_lines(VAULT / "Logs" / "orchestrator.log"))
            logs.extend(tail_lines(VAULT / "Logs" / "file_drop_watcher.log"))
            return json_response(self, {"lines": logs[-60:]})
        if path == "/api/vault-path":
            return json_response(self, {"vault": str(VAULT)})
        if path == "/api/health":
            return json_response(self, {"status": "ok"})
        if path == "/api/claude/status":
            return json_response(self, status_claude())
        if path == "/api/claude/logs":
            claude_log = VAULT / "Logs" / "claude_cli.log"
            return json_response(self, {"lines": tail_lines(claude_log)})
        return json_response(self, {"error": "not found"}, status=404)

    def handle_api_post(self, path: str) -> None:
        payload = read_json_body(self)
        if path == "/api/approve":
            rel_path = payload.get("path", "")
            ok, result = move_item(rel_path, VAULT / "Approved")
            status = 200 if ok else 400
            return json_response(self, {"ok": ok, "path": result}, status=status)
        if path == "/api/reject":
            rel_path = payload.get("path", "")
            ok, result = move_item(rel_path, VAULT / "Rejected")
            status = 200 if ok else 400
            return json_response(self, {"ok": ok, "path": result}, status=status)
        if path == "/api/new-task":
            title = payload.get("title", "New Task")
            body = payload.get("body", "")
            task_type = payload.get("type", "task")
            path_created = create_task(title, body, task_type)
            process_tasks(VAULT)
            return json_response(self, {"ok": True, "path": path_created})
        if path == "/api/run-orchestrator":
            count = process_tasks(VAULT)
            return json_response(self, {"ok": True, "planned": count})
        if path == "/api/create-app":
            language = payload.get("language", "")
            name = payload.get("name", "")
            command = payload.get("command", "")
            allow_command = bool(payload.get("allow_command", False))
            result = run_create_app(language, name, command, allow_command)
            status = 200 if result.get("ok") else 400
            return json_response(self, result, status=status)
        if path == "/api/new-claude-task":
            language = payload.get("language", "")
            name = payload.get("name", "")
            instruction = payload.get("instruction", "")
            if not language or not name:
                return json_response(self, {"ok": False, "error": "Language and name required."}, status=400)
            task_path = create_claude_app_task(language, name, instruction)
            update_queue_signal(task_path, instruction)
            process_tasks(VAULT)
            notify_claude(task_path)
            return json_response(self, {"ok": True, "path": task_path})
        if path == "/api/claude/start":
            return json_response(self, start_claude())
        if path == "/api/claude/stop":
            return json_response(self, stop_claude())
        if path == "/api/claude/ensure":
            return json_response(self, ensure_claude())
        if path == "/api/complete-task":
            rel_path = payload.get("path", "")
            ok, result = move_item(rel_path, VAULT / "Done")
            status = 200 if ok else 400
            return json_response(self, {"ok": ok, "path": result}, status=status)
        return json_response(self, {"error": "not found"}, status=404)


def main() -> None:
    load_env_file(REPO_ROOT / ".env")
    load_env_file(DASHBOARD_DIR / ".env")
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", "8787"))
    autostart = os.getenv("DASHBOARD_CLAUDE_AUTOSTART", "false").lower() in {"1", "true", "yes"}
    watchdog = os.getenv("DASHBOARD_CLAUDE_WATCHDOG", "false").lower() in {"1", "true", "yes"}
    watchdog_interval = int(os.getenv("DASHBOARD_CLAUDE_WATCHDOG_INTERVAL", "10"))
    orchestrator_auto = os.getenv("DASHBOARD_ORCHESTRATOR_AUTORUN", "false").lower() in {"1", "true", "yes"}
    orchestrator_interval = int(os.getenv("DASHBOARD_ORCHESTRATOR_INTERVAL", "60"))
    executor_auto = os.getenv("DASHBOARD_EXECUTOR_AUTORUN", "false").lower() in {"1", "true", "yes"}
    executor_interval = int(os.getenv("DASHBOARD_EXECUTOR_INTERVAL", "30"))
    if autostart:
        start_claude()
    if watchdog:
        thread = threading.Thread(
            target=_watchdog_loop,
            args=(watchdog_interval,),
            daemon=True,
        )
        thread.start()
    if orchestrator_auto:
        thread = threading.Thread(
            target=_orchestrator_loop,
            args=(orchestrator_interval,),
            daemon=True,
        )
        thread.start()
    if executor_auto:
        thread = threading.Thread(
            target=_executor_loop,
            args=(executor_interval,),
            daemon=True,
        )
        thread.start()
    with TCPServer((host, port), DashboardHandler) as httpd:
        print(f"Dashboard running at http://{host}:{port}")
        httpd.serve_forever()


def _watchdog_loop(interval: int) -> None:
    while True:
        ensure_claude()
        time.sleep(max(5, interval))


def _orchestrator_loop(interval: int) -> None:
    while True:
        process_tasks(VAULT)
        time.sleep(max(10, interval))


def _executor_loop(interval: int) -> None:
    while True:
        process_executable_tasks(VAULT, send_claude_prompt)
        time.sleep(max(10, interval))


if __name__ == "__main__":
    main()
