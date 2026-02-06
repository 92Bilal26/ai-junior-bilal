---
id: 0009
title: Setup app workspace
stage: green
date: 2026-01-30
surface: agent
model: gpt-5
feature: ai-employee
branch: master
user: Muhammad Bilal
command: direct
labels: [apps, scaffolding, structure]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - apps/README.md
 - apps/laravel/.gitkeep
 - apps/java/.gitkeep
 - apps/react/.gitkeep
 - apps/ai/.gitkeep
 - apps/backend/.gitkeep
 - apps/frontend/.gitkeep
 - scripts/create-app.ps1
 - scripts/README.md
tests:
 - none
---

## Prompt

i want keep open mind any aap at any frame work claude cli can create so first solve problem local development by instruction and chose for aver new app create new folder and first create main folder realted to ai-employe development then create language wise folder laravel ,java, react, ai etc when we create any app realted to programming languaget then it create it in realted folder then in realted folder create app folder name when we start this

## Response snapshot

Created a workspace structure under apps/ with language folders and added a script to create new app folders with optional scaffold commands.

## Outcome

- ✅ Impact: Standardized app workspace and creation workflow.
- 🧪 Tests: none
- 📁 Files: apps structure and create-app script added.
- 🔁 Next prompts: scaffold first app with selected framework CLI.
- 🧠 Reflection: Consistent structure prevents clutter and speeds setup.

## Evaluation notes (flywheel)

- Failure modes observed: None.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a JSON registry of created apps.
