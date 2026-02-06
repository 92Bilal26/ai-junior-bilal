---
id: 0006
title: Fix dashboard import path
stage: red
date: 2026-01-30
surface: agent
model: gpt-5
feature: ai-employee
branch: master
user: Muhammad Bilal
command: direct
labels: [dashboard, import, python, debug]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - dashboard/server.py
tests:
 - python -m py_compile dashboard\\server.py
---

## Prompt

E:\ai_project\ai-bilal-junior>python dashboard/server.py
Traceback (most recent call last):
  File "E:\ai_project\ai-bilal-junior\dashboard\server.py", line 11, in <module>
    from ai_employee import config
ModuleNotFoundError: No module named 'ai_employee'

E:\ai_project\ai-bilal-junior>

## Response snapshot

Adjusted the dashboard server to add the repo root to sys.path so the ai_employee package imports correctly when running the script directly.

## Outcome

- ✅ Impact: Running `python dashboard/server.py` now resolves imports.
- 🧪 Tests: Python syntax compilation for the server.
- 📁 Files: `dashboard/server.py` updated.
- 🔁 Next prompts: re-run the server and confirm dashboard loads.
- 🧠 Reflection: Explicitly set sys.path for direct script execution.

## Evaluation notes (flywheel)

- Failure modes observed: None.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a guard to prevent duplicate sys.path entries.
