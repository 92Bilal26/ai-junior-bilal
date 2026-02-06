# AI Employee Vault

This folder is the local system of record for the AI employee.

## Key folders
- `Needs_Action/` incoming tasks
- `Plans/` generated plans and drafts
- `Pending_Approval/` approvals required before action
- `Approved/` approved items
- `Rejected/` rejected items
- `Done/` completed tasks
- `Logs/` watcher/orchestrator logs
- `Inbox/` manual drops or notes
  - `Inbox/Drop/` file-drop watcher input
- `Signals/` runtime signals (e.g., Claude queue notifications)

## Quick start
1) Drop a markdown task into `Needs_Action/`.
2) The orchestrator will create a plan in `Plans/`.
3) If approval is needed, it writes a file in `Pending_Approval/`.
