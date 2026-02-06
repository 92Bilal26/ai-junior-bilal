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

## Features

### Core Watchers
- **File Drop Watcher**: Monitor folder for dropped files
- **ESS Attendance Watcher**: Auto-detect and mark attendance in ESS system (new!)

### ESS Attendance Marking (NEW)
Automatically monitor and mark your attendance in ESS (Employee Self-Service):
- Runs every 60 seconds by default
- Uses Playwright for secure browser automation
- Human-in-the-loop approval workflow (move file to `/Approved` to execute)
- Full audit logging

**Setup:**
```bash
# 1. Configure ESS credentials in .env
ESS_USER_ID=21457
ESS_PASSWORD=your_password

# 2. Install Playwright
pip install playwright
python -m playwright install chromium

# 3. Start watcher and executor
python -m ai_employee.watchers.ess_watcher
python -m ai_employee.approval_executor
```

**Usage:**
- Attendance approval tasks appear in `vault/Needs_Action/ATTENDANCE_MARK_*.md`
- Review and move to `vault/Approved/` to mark attendance
- Check results in `vault/Done/` or `vault/Rejected/`

See `docs/ESS_ATTENDANCE_FEATURE.md` for full documentation.

## Notes
- Keep credentials in `.env` (never commit).
- All sensitive actions require approval.
- ESS credentials stored locally only, never shared with Claude or external services.
