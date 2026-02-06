---
id: 0013
title: Watchdog logs and autoload
stage: green
date: 2026-01-30
surface: agent
model: gpt-5
feature: ai-employee
branch: master
user: Muhammad Bilal
command: direct
labels: [claude, watchdog, logs, autoload]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - ai_employee/claude_runner.py
 - dashboard/server.py
 - dashboard/index.html
 - dashboard/styles.css
 - dashboard/app.js
 - .env.example
 - README.md
 - .gitignore
 - vault/Signals/.gitkeep
 - vault/README.md
tests:
 - python -m py_compile ai_employee\\claude_runner.py dashboard\\server.py
---

## Prompt

yes plz nex add a watchdog,live log viewer and auto load queuent tasks for claude i give task by dasboard it just careate task md dont start working on it it all control auto by orchesto agent which will manage it

## Response snapshot

Added a Claude watchdog loop, live log viewer for Claude CLI output, and automatic queue signaling with optional Claude prompt injection; also added orchestrator auto-run config.

## Outcome

- ✅ Impact: Claude can be auto-restarted, logs are viewable live, and queued tasks trigger a Claude notification without auto-execution.
- 🧪 Tests: Python syntax compilation for updated modules.
- 📁 Files: Runner, dashboard UI/backend, config, and vault signals updated.
- 🔁 Next prompts: enable env flags and verify behavior end-to-end.
- 🧠 Reflection: Use env flags to guard automation and avoid unintended execution.

## Evaluation notes (flywheel)

- Failure modes observed: None.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add an explicit "plan-only" mode flag in the task frontmatter.
