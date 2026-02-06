---
id: 0012
title: Autostart claude from dashboard
stage: green
date: 2026-01-30
surface: agent
model: gpt-5
feature: ai-employee
branch: master
user: Muhammad Bilal
command: direct
labels: [claude, dashboard, autostart]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - ai_employee/claude_runner.py
 - dashboard/server.py
 - dashboard/index.html
 - dashboard/app.js
 - .env.example
 - README.md
tests:
 - python -m py_compile ai_employee\\claude_runner.py dashboard\\server.py
---

## Prompt

i will not run claude my self when i start this ai employee app it should start claude with starting then this calude have agent,sub agents ,skill which will controll tasks in this ai employee app

## Response snapshot

Added a Claude runner that can start/stop Claude from the dashboard, wired endpoints and UI buttons, and added an autostart option via environment variable.

## Outcome

- ✅ Impact: Claude CLI can now be launched automatically or via dashboard controls.
- 🧪 Tests: Python syntax compilation for new modules.
- 📁 Files: Claude runner + dashboard wiring + config docs.
- 🔁 Next prompts: configure CLAUDE_CLI path and verify autostart behavior.
- 🧠 Reflection: Keep launch guarded by env flags and status checks.

## Evaluation notes (flywheel)

- Failure modes observed: None.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a health check that detects if Claude has exited unexpectedly.
