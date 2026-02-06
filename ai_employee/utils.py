from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def log_line(path: Path, message: str) -> None:
    ensure_dir(path.parent)
    stamp = utc_now_iso()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text
    fm_lines = []
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            break
        fm_lines.append(lines[i])
        i += 1
    if i >= len(lines):
        return {}, text
    body = "\n".join(lines[i + 1 :])
    fm: Dict[str, str] = {}
    for line in fm_lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip()
    return fm, body


def render_frontmatter(fm: Dict[str, str], body: str) -> str:
    lines = ["---"]
    for key in sorted(fm.keys()):
        lines.append(f"{key}: {fm[key]}")
    lines.append("---")
    lines.append(body.lstrip("\n"))
    return "\n".join(lines).rstrip() + "\n"


def slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_").lower() or "task"
