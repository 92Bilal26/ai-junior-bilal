# AI Employee (Junior) - Spec

## Summary
Build a local-first AI "junior" that follows your instructions to manage Gmail, WhatsApp, GitHub work (code, commit, push), and Word/Excel updates (local + OneDrive), with human-in-the-loop approvals and audit logs.

## Goals
- Centralize all tasks into a single, file-based workflow (vault) that is easy to audit.
- Support instruction-following for coding tasks across existing projects (Next.js/Laravel/Java/AI).
- Draft and send communications only with explicit approval.
- Create/update Word and Excel files via safe, repeatable automation.
- Provide a predictable, extensible skill system for new tasks and new projects.

## Non-goals
- Fully autonomous payments or irreversible actions without approval.
- Breaking provider terms of service (e.g., WhatsApp automation without consent).
- Storing secrets in the repo (tokens, credentials).

## Users and Actors
- Primary user (you): reviews approvals, provides instructions, and validates output.
- AI Junior (agent): reads tasks, plans, drafts outputs, and requests approvals.
- Watchers: lightweight scripts that create tasks from external signals.
- Action adapters (MCP or scripts): perform approved actions (send email, git push).

## Inputs and Outputs
Inputs:
- Task files in `vault/Needs_Action/`
- Instructions from you (manual or watcher generated)
- Source code repositories on disk
- Office documents on disk

Outputs:
- Drafts and plans in `vault/Plans/`
- Approval requests in `vault/Pending_Approval/`
- Final artifacts (emails sent, code changes, updated docs)
- Logs in `vault/Logs/`

## Functional Requirements
FR-1: Convert instructions into a concrete, multi-step plan with checkboxes.
FR-2: Draft email replies and place them in `Pending_Approval` before sending.
FR-3: Update code in existing projects and create commits locally.
FR-4: Push to GitHub only after approval (or per approved policy).
FR-5: Draft WhatsApp responses (send only after approval).
FR-6: Create/update Word and Excel files from instructions.
FR-7: Maintain an audit trail for all actions.
FR-8: Allow new skills to be added without changing the core workflow.

## Non-Functional Requirements
- Local-first: all task state stored in local markdown files.
- Human-in-the-loop for sensitive actions (email send, WhatsApp send, git push).
- Observability: structured logs for watcher and orchestrator activity.
- Reliability: recover gracefully from crashes; no data loss.

## Data and Storage
- Vault: `vault/` folder is the system of record.
- Secrets: stored in `.env` (not checked in).
- State: minimal state files under `.state/` (not checked in).

## Security and Compliance
- Least-privilege tokens for GitHub and Gmail.
- No automated payment execution without explicit approval.
- Respect app terms of service; avoid prohibited automation.

## Open Questions
1) Which Gmail account should be used (and do you want read-only or read+send)?
2) Confirm GitHub repos to control (path: https://github.com/92Bilal26) and any repo-specific rules.
3) OneDrive: use Microsoft 365/Graph API or sync to local disk and update locally?
4) WhatsApp: draft-only or send-after-approval with browser automation?
5) Where are your existing projects located on disk (paths)?
