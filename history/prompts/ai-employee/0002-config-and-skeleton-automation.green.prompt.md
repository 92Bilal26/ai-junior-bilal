---
id: 0002
title: Config and skeleton automation
stage: green
date: 2026-01-29
surface: agent
model: gpt-5
feature: ai-employee
branch: master
user: Muhammad Bilal
command: direct
labels: [gmail, github, onedrive, watcher, orchestrator]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .gitignore
 - .env.example
 - README.md
 - specs/ai-employee/spec.md
 - specs/ai-employee/plan.md
 - vault/README.md
 - vault/Company_Handbook.md
 - vault/Inbox/Drop/.gitkeep
 - ai_employee/__init__.py
 - ai_employee/config.py
 - ai_employee/utils.py
 - ai_employee/watchers/__init__.py
 - ai_employee/watchers/base.py
 - ai_employee/watchers/file_drop_watcher.py
 - ai_employee/orchestrator.py
tests:
 - python -m py_compile ai_employee\\config.py ai_employee\\utils.py ai_employee\\watchers\\base.py ai_employee\\watchers\\file_drop_watcher.py ai_employee\\orchestrator.py
---

## Prompt

1. gmail,2.https://github.com/92Bilal26 this github is path yes require approval for it ,3.on both local and onedrive should be used

## Response snapshot

Updated the spec/plan for Gmail, GitHub approvals, and OneDrive + local docs, and implemented the initial watcher/orchestrator skeleton with config scaffolding and vault drop folder support.

## Outcome

- ✅ Impact: Basic automation skeleton and configuration scaffolding added.
- 🧪 Tests: Python syntax compilation for new modules.
- 📁 Files: Spec/plan updates, watcher/orchestrator code, config, and .gitignore.
- 🔁 Next prompts: Provide project paths and decide OneDrive access method (Graph vs local sync).
- 🧠 Reflection: Start with safe local pipeline before wiring external APIs.

## Evaluation notes (flywheel)

- Failure modes observed: None.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a sample task and verify plan generation end-to-end.
