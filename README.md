# AI Employee (Junior)

Local-first AI assistant that plans and routes work through a markdown vault with approvals.

## Quick start
1) Copy `.env.example` to `.env` and adjust paths.
2) Drop a file into `vault/Inbox/Drop/`.
3) Run the watcher once:
   - `python ai_employee/watchers/file_drop_watcher.py --once`
4) Run the orchestrator once:
   - `python ai_employee/orchestrator.py --once`
5) Check `vault/Plans/` for a generated plan.

## Dashboard
Run the local dashboard backend:
- `python dashboard/server.py`
Then open `http://127.0.0.1:8787` in your browser.

The dashboard auto-loads environment variables from `.env` if present.
You can place `.env` in the repo root or inside the `dashboard/` folder.

### Developer console (Create App)
Use the Developer Console to queue a Claude task that describes the app to build.
After queuing, run `claude` in the repo root and follow the task in `vault/Needs_Action/`.

### Auto-start Claude (optional)
If you want the dashboard to start Claude automatically:
- Set `DASHBOARD_CLAUDE_AUTOSTART=true`
- Ensure `CLAUDE_CLI=claude` (or the full path)

### Watchdog + auto-load + orchestrator auto-run (optional)
- `DASHBOARD_CLAUDE_WATCHDOG=true` to restart Claude if it exits
- `DASHBOARD_CLAUDE_WATCHDOG_INTERVAL=10` (seconds)
- `CLAUDE_AUTOLOAD=true` to notify Claude when new tasks are queued
- `DASHBOARD_ORCHESTRATOR_AUTORUN=true` to run the orchestrator loop
- `DASHBOARD_ORCHESTRATOR_INTERVAL=60` (seconds)
- `CLAUDE_FORCE_RESTART=true` to restart Claude if it is running but not attached to the dashboard

## Notes
- Keep credentials in `.env` (never commit).
- All sensitive actions require approval.
