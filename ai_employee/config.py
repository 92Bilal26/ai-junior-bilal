from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    env_root = os.getenv("AI_EMPLOYEE_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _repo_root()
VAULT_PATH = Path(os.getenv("VAULT_PATH", REPO_ROOT / "vault")).expanduser().resolve()
DROP_FOLDER = Path(os.getenv("DROP_FOLDER", VAULT_PATH / "Inbox" / "Drop")).expanduser().resolve()
LOG_DIR = Path(os.getenv("LOG_DIR", VAULT_PATH / "Logs")).expanduser().resolve()
STATE_DIR = Path(os.getenv("STATE_DIR", REPO_ROOT / ".state")).expanduser().resolve()

GMAIL_CREDENTIALS = os.getenv("GMAIL_CREDENTIALS", "")
GITHUB_REPO_ROOTS = os.getenv("GITHUB_REPO_ROOTS", "")

# Document roots
LOCAL_DOC_ROOT = Path(os.getenv("LOCAL_DOC_ROOT", REPO_ROOT)).expanduser().resolve()
ONEDRIVE_ROOT = os.getenv("ONEDRIVE_ROOT", "")
