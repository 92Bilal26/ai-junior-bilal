# AI Employee (Junior) - Architecture Plan

## 1) Scope and Dependencies
In Scope:
- Local vault-based workflow for tasks, plans, approvals, logs.
- Watchers to create tasks from external signals (initially file-drop).
- Orchestrator to read tasks and produce plans/drafts.
- Action adapters for email drafts, git commit/push, WhatsApp drafts, Office file updates.

Out of Scope:
- Fully autonomous, irreversible actions without approval.
- Any automation that violates provider terms (WhatsApp risk noted).

External Dependencies:
- Git (local), GitHub (remote).
- Gmail API for email.
- Office doc tooling (`python-docx`, `openpyxl`) and/or Microsoft Graph for OneDrive.
- Optional: Playwright for WhatsApp Web (requires explicit approval).

## 2) Key Decisions and Rationale
Decision: Local-first, file-based state in `vault/`.
Options: database vs files.
Trade-offs: Files are transparent and easy to audit; database adds complexity.

Decision: Human-in-the-loop approvals for send/post/push.
Options: auto-send vs approval gate.
Trade-offs: Approval adds latency but reduces risk.

Decision: Watcher + Orchestrator pipeline.
Options: synchronous CLI only vs always-on watchers.
Trade-offs: Watchers allow proactive tasks; adds process management needs.

## 3) Interfaces and Contracts
Task file (input) contract:
- Markdown with frontmatter: `type`, `source`, `priority`, `status`, `created_at`.

Plan file (output) contract:
- Checklist steps, expected outputs, approval requirement.

Approval files:
- Stored in `vault/Pending_Approval/` with explicit action summary and risk.

## 4) NFRs and Budgets
Performance:
- Task ingestion < 30s for watcher polling.
Reliability:
- Watchers restart automatically; no task loss.
Security:
- Tokens in `.env`, never in repo.
Cost:
- Prefer local tools; use APIs only when required.

## 5) Data Management
Source of truth: `vault/` folder.
Retention: keep logs for 90 days (configurable).
Migration: versioned task schemas when fields change.

## 6) Operational Readiness
Observability:
- Logs per watcher and orchestrator.
Alerting:
- Error log entries create a `Needs_Action` item.
Deployment:
- Local runs via scheduled tasks or process manager (PM2).

## 7) Risk Analysis
Risk 1: WhatsApp automation ToS violations.
Mitigation: Draft-only mode unless user explicitly opts in.
Risk 2: Token leakage.
Mitigation: `.env` only, `.gitignore` enforced.
Risk 3: Unintended git push.
Mitigation: approval gate and dry-run checks.

## 8) Evaluation and Validation
Definition of Done:
- Vault structure exists and is usable.
- At least one watcher creates tasks.
- Orchestrator produces a plan file from a task.
- Approval workflow demonstrated end-to-end.

## 9) Phased Delivery
Phase 0 (this sprint):
- Create vault structure and baseline docs.
- Add a file-drop watcher (polling).
- Orchestrator stub that reads tasks and generates plan files.

Phase 1:
- Email draft skill + approval.
- Git commit skill + approval.
- Word/Excel update skill.

Phase 2:
- WhatsApp draft skill.
- GitHub push skill with approval.
- Scheduler + process manager setup.
