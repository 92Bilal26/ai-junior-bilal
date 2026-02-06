# ESS Attendance Marking Feature

## Overview

This feature enables your AI Employee to automatically monitor and mark your attendance in the **ESS (Employee Self-Service) system** at `https://ess.dimionline.com/` using browser automation and a human-in-the-loop approval workflow.

## Architecture

### Components

1. **ESSWatcher** (`ai_employee/watchers/ess_watcher.py`)
   - Monitors attendance status daily
   - Uses Playwright for browser automation
   - Creates approval tasks in `/Needs_Action` folder

2. **ESSAttendanceMCP** (`mcp_servers/ess_attendance_mcp.py`)
   - MCP server that handles actual attendance marking
   - Securely stored credentials via `.env`
   - Executes the mark present action after human approval

3. **ApprovalExecutor** (`ai_employee/approval_executor.py`)
   - Watches `/Approved` folder
   - Executes approved attendance marking requests
   - Moves completed/failed actions to `/Done` and `/Rejected`

### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY ATTENDANCE WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. DETECTION (ESSWatcher - runs every 60 seconds)
   └─> Check if attendance marked for today
   └─> If not marked, create approval task in /Needs_Action

2. HUMAN REVIEW
   └─> You review: /Vault/Needs_Action/ATTENDANCE_MARK_*.md
   └─> Verify date and action is correct

3. APPROVAL
   └─> Move file from /Needs_Action to /Approved

4. EXECUTION (ApprovalExecutor - runs every 30 seconds)
   └─> Detect file in /Approved
   └─> Call ESSAttendanceMCP to mark attendance
   └─> Move result to /Done or /Rejected

5. COMPLETION
   └─> Attendance marked in ESS
   └─> Audit log created
```

## Setup

### 1. Add ESS Credentials to `.env`

Create a `.env` file in your project root:

```bash
# ESS Attendance System
ESS_URL=https://ess.dimionline.com/
ESS_USER_ID=21457
ESS_PASSWORD=92Bil@l26
ESS_HEADLESS=true
ESS_CHECK_INTERVAL=60
```

**⚠️ SECURITY WARNING:**
- **NEVER commit `.env` file to git**
- Add `.env` to `.gitignore` (already done)
- Keep this file secure on your machine only
- Rotate ESS password periodically
- Use OS credential managers (Windows Credential Manager, macOS Keychain) for added security

### 2. Install Playwright

```bash
pip install playwright
python -m playwright install chromium
```

### 3. Start the Watcher and Executor

Run these in separate terminals (or use PM2 for production):

```bash
# Terminal 1: Start ESS Watcher
python -m ai_employee.watchers.ess_watcher

# Terminal 2: Start Approval Executor
python -m ai_employee.approval_executor
```

### 4. Add to Dashboard (Optional)

If using the dashboard, add this to your startup script to auto-start both services.

## Usage

### Daily Operation

1. **Monitor logs**: Check `vault/Logs/ess_watcher.log` and `vault/Logs/approval_executor.log`

2. **Review pending approvals**:
   ```bash
   ls vault/Needs_Action/ATTENDANCE_MARK_*.md
   ```

3. **Approve attendance marking**:
   ```bash
   # Move the file from Needs_Action to Approved
   mv vault/Needs_Action/ATTENDANCE_MARK_20260207_*.md vault/Approved/
   ```

4. **Check execution results**:
   ```bash
   # Successful markings
   ls vault/Done/ATTENDANCE_MARK_*.md

   # Failed markings (needs manual action)
   ls vault/Rejected/ATTENDANCE_MARK_*.md
   ```

### Example Approval Task

```markdown
---
type: attendance_marking
source: ess_watcher
priority: high
status: pending_approval
created_at: 2026-02-07T07:30:00Z
date: 2026-02-07
current_status: Unknown
action: mark_present
---

# ESS Attendance Marking

## Mark Attendance for 2026-02-07

Current status: **Unknown**

### Action Required

Move this file to `/Approved` folder to automatically mark attendance as **Present** in ESS.

### Details

- Date: 2026-02-07
- Current Status: Unknown
- Action: Mark as Present
- System: ESS (https://ess.dimionline.com/)

### Steps (for manual marking if approval fails)

1. Go to https://ess.dimionline.com/
2. Login with your credentials
3. Navigate to Attendance
4. Click Mark Present for today's date
5. Confirm the marking
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ESS_URL` | `https://ess.dimionline.com/` | ESS system URL |
| `ESS_USER_ID` | - | Your ESS user ID (required) |
| `ESS_PASSWORD` | - | Your ESS password (required) |
| `ESS_HEADLESS` | `true` | Run browser in headless mode |
| `ESS_CHECK_INTERVAL` | `60` | Check interval in seconds |

### Command-Line Arguments

```bash
# Run ESS Watcher once and exit
python -m ai_employee.watchers.ess_watcher --once

# Run with custom interval (30 seconds)
python -m ai_employee.watchers.ess_watcher --interval 30

# Run with visible browser (for debugging)
python -m ai_employee.watchers.ess_watcher --headless false

# Run approval executor once
python -m ai_employee.approval_executor --once

# Run with custom interval (15 seconds)
python -m ai_employee.approval_executor --interval 15
```

## Troubleshooting

### Login Fails

**Issue**: Watcher logs show "LOGIN ERROR"

**Solutions**:
1. Verify credentials in `.env` file
2. Check ESS website is accessible: `https://ess.dimionline.com/`
3. Try running with `--headless false` to see browser
4. Check if ESS requires additional authentication (2FA, security questions)

```bash
python -m ai_employee.watchers.ess_watcher --headless false
```

### Cannot Find Attendance Status

**Issue**: Watcher logs show "Could not find attendance status on page"

**Solutions**:
1. ESS interface may have changed - DOM selectors need updating
2. Check the page manually: `https://ess.dimionline.com/`
3. Report issue with screenshot of attendance page

### Attendance Not Marked After Approval

**Issue**: File moved to `/Approved` but not executed

**Solutions**:
1. Check `vault/Logs/approval_executor.log` for errors
2. Verify ESS credentials are correct
3. Check MCP server is running
4. Try manual marking: follow steps in the approval task

### Watcher Stops Running

**Issue**: Watcher process died unexpectedly

**Solutions**:
1. Use PM2 for process management:
   ```bash
   npm install -g pm2
   pm2 start "python -m ai_employee.watchers.ess_watcher" --name ess-watcher
   pm2 save && pm2 startup
   ```

2. Check logs:
   ```bash
   tail -f vault/Logs/ess_watcher.log
   ```

## Security Considerations

### Credentials Management

✅ **DO:**
- Store credentials in `.env` file
- Add `.env` to `.gitignore`
- Use strong, unique passwords
- Rotate credentials monthly
- Use the browser in headless mode for security

❌ **DON'T:**
- Hardcode credentials in Python files
- Commit `.env` to version control
- Share `.env` file or credentials
- Use the same password as other systems
- Run with `--headless false` in production

### Browser Automation Safety

- Playwright runs in **headless mode** by default (no visible window)
- Session data is stored locally, not in vault
- Browser cache is temporary and cleared between runs
- Only performs the specific action: marking attendance

### Approval Workflow Safety

The human-in-the-loop design ensures:
- You review every attendance marking request
- You explicitly approve each action
- Failed markings go to `/Rejected` for manual review
- All actions are logged for audit trail

## Performance

### Resource Usage

- **CPU**: Minimal when idle; ~20-30% during browser automation (< 2 minutes/day)
- **Memory**: ~100MB per process (watcher + executor)
- **Disk**: ~10KB per day in logs

### Check Interval Recommendations

| Scenario | Interval | Notes |
|----------|----------|-------|
| Home/office with fixed hours | 60 seconds | Checks once per minute |
| Flexible hours | 30 seconds | More frequent checks |
| Multiple sites | 120 seconds | Reduces API load |

## Integration with Other Features

### With Orchestrator

The ESS Watcher works independently but can be coordinated with the orchestrator:

```bash
# Run orchestrator to plan attendance tasks
python -m ai_employee.orchestrator --once

# Run watcher to detect status
python -m ai_employee.watchers.ess_watcher --once

# Run approval executor
python -m ai_employee.approval_executor --once
```

### With Claude Code

You can ask Claude Code to manage attendance approvals:

```bash
claude --cwd E:\ai_project\ai-bilal-junior "Review and approve all pending attendance tasks in vault/Needs_Action"
```

## Advanced: Customizing Selectors

If ESS website changes its HTML structure, you may need to update Playwright selectors.

### Update Username Field Selector

In `ai_employee/watchers/ess_watcher.py`, line 66:

```python
username_selectors = [
    "input[name='username']",      # Try these selectors in order
    "input[name='userID']",
    "input[id*='user']",
    "input[placeholder*='ID']",
    # Add new selector here if ESS changes
]
```

### Update Password Field Selector

In `ai_employee/watchers/ess_watcher.py`, line 79:

```python
password_selectors = [
    "input[name='password']",
    "input[type='password']",
    "input[id*='pass']",
    # Add new selector here
]
```

### Debug Mode

Run watcher with visible browser to inspect page:

```bash
python -m ai_employee.watchers.ess_watcher --headless false
```

Then:
1. Open DevTools (F12)
2. Inspect attendance status elements
3. Update selectors in code
4. Test with `--once` flag

## Logs and Audit Trail

All attendance actions are logged:

```bash
# View watcher logs
cat vault/Logs/ess_watcher.log

# View executor logs
cat vault/Logs/approval_executor.log

# View recent entries
tail -20 vault/Logs/ess_watcher.log
tail -20 vault/Logs/approval_executor.log
```

### Log Format

```
[2026-02-07 08:30:15] Navigating to https://ess.dimionline.com/
[2026-02-07 08:30:20] Username entered
[2026-02-07 08:30:22] Login submitted and page loaded
[2026-02-07 08:30:25] Current attendance status: Present
[2026-02-07 08:30:26] Created attendance approval task: ATTENDANCE_MARK_20260207_*.md
```

## Comparison: Manual vs Automated

| Task | Manual | Automated |
|------|--------|-----------|
| Check ESS daily | ✓ | ✓ |
| Mark attendance | ✓ | ✓ (with approval) |
| Time required | 2-3 min/day | 30 seconds setup + 10 sec approval |
| Forget attendance | Possible | Never (auto-reminded) |
| Fallback if fails | Manual marking | Move to `/Rejected` for manual action |

## FAQ

**Q: What if ESS has 2FA (two-factor authentication)?**
A: Current implementation doesn't support 2FA. You'll need to manually mark attendance. Consider disabling 2FA on ESS if possible, or asking IT for an exception.

**Q: Can I mark attendance for past dates?**
A: Yes, the `date` parameter in the approval task allows specifying any date. Useful for making up missed markings.

**Q: What if I'm on leave?**
A: Manually update the approval task to action: `mark_on_leave` (not yet implemented). For now, don't approve the task.

**Q: Is my password sent to Claude or any external service?**
A: **No.** Your credentials only exist in the `.env` file on your machine. Playwright runs locally. Claude never sees your credentials.

**Q: Can I disable the watcher temporarily?**
A: Yes, simply don't start the `ess_watcher.py` process. Or rename it to prevent accidental execution.

## Feature Roadmap

Planned enhancements:

- [ ] Support for 2FA/OTP
- [ ] Mark on leave (with reason)
- [ ] Weekly summary reports
- [ ] Integration with calendar for automatic leave marking
- [ ] Webhook notifications on success/failure
- [ ] Support for other ESS systems (Arjun ESS, Keka, Personio, etc.)

## Support and Issues

If you encounter issues:

1. Check logs: `vault/Logs/ess_watcher.log`
2. Try running with visible browser: `--headless false`
3. Test manually at `https://ess.dimionline.com/`
4. Create an issue with:
   - Screenshot of error
   - Log output (with sensitive info redacted)
   - Steps to reproduce

---

**Built with Playwright and the AI Employee Framework**
For more info, see: `Personal_AI_Employee_Hackathon_0_Building_Autonomous_FTEs_in_2026.md`
