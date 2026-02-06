from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from pathlib import Path

from ai_employee import config
from ai_employee.utils import ensure_dir, log_line, utc_now_iso


STATE_PATH = config.STATE_DIR / "claude_runner.json"
LOG_PATH = config.VAULT_PATH / "Logs" / "claude_runner.log"
CLAUDE_LOG_PATH = config.VAULT_PATH / "Logs" / "claude_cli.log"

_process: subprocess.Popen | None = None
_stdin_lock = threading.Lock()


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    ensure_dir(STATE_PATH.parent)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start() -> dict:
    global _process
    state = _load_state()
    pid = int(state.get("pid", 0) or 0)
    if pid and _pid_exists(pid):
        return {"ok": True, "status": "already_running", "pid": pid}

    claude_cmd = os.getenv("CLAUDE_CLI", "claude")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    ensure_dir(CLAUDE_LOG_PATH.parent)
    log_handle = CLAUDE_LOG_PATH.open("a", encoding="utf-8")

    try:
        process = subprocess.Popen(
            [claude_cmd],
            cwd=str(config.REPO_ROOT),
            stdin=subprocess.PIPE,
            stdout=log_handle,
            stderr=log_handle,
            creationflags=creationflags,
            text=True,
        )
    except FileNotFoundError:
        log_line(LOG_PATH, f"Claude CLI not found: {claude_cmd}")
        log_handle.close()
        return {"ok": False, "status": "not_found", "error": "Claude CLI not found"}
    _process = process
    state = {"pid": process.pid, "started_at": utc_now_iso(), "log_path": str(CLAUDE_LOG_PATH)}
    _save_state(state)
    log_line(LOG_PATH, f"Claude started pid={process.pid}")
    return {"ok": True, "status": "started", "pid": process.pid}


def stop() -> dict:
    global _process
    state = _load_state()
    pid = int(state.get("pid", 0) or 0)
    if not pid:
        return {"ok": False, "status": "not_running"}

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    log_line(LOG_PATH, f"Claude stopped pid={pid}")
    _save_state({})
    _process = None
    return {"ok": True, "status": "stopped", "pid": pid}


def status() -> dict:
    state = _load_state()
    pid = int(state.get("pid", 0) or 0)
    running = _pid_exists(pid) if pid else False
    return {
        "ok": True,
        "pid": pid if running else 0,
        "running": running,
        "started_at": state.get("started_at"),
    }


def send_prompt(text: str) -> dict:
    if not text.strip():
        return {"ok": False, "error": "empty prompt"}
    if _process is None or _process.poll() is not None:
        return {"ok": False, "error": "Claude is not running in this session"}
    if _process.stdin is None:
        return {"ok": False, "error": "Claude stdin not available"}
    with _stdin_lock:
        _process.stdin.write(text.rstrip() + "\n")
        _process.stdin.flush()
    log_line(LOG_PATH, "Prompt sent to Claude.")
    return {"ok": True}


def ensure_running() -> dict:
    state = status()
    if state.get("running"):
        if _process is None:
            restart = os.getenv("CLAUDE_FORCE_RESTART", "true").lower() in {"1", "true", "yes"}
            if restart:
                stop()
                return start()
        return {"ok": True, "status": "already_running", "pid": state.get("pid")}
    return start()
