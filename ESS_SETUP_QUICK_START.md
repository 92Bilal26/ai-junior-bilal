# ESS Attendance - Quick Start Guide

Get your AI Employee automatically marking attendance in 5 minutes.

## Step 1: Configure Credentials

Create/update `.env` file in project root with your ESS credentials:

```bash
# ESS Attendance System
ESS_URL=https://ess.dimionline.com/
ESS_USER_ID=21457
ESS_PASSWORD=92Bil@l26
ESS_HEADLESS=true
ESS_CHECK_INTERVAL=60
```

**⚠️ Security Reminder:**
- `.env` is already in `.gitignore` - NEVER commit it
- Keep this file secure and private
- You're the only one who should have these credentials

## Step 2: Install Playwright

```bash
# Install playwright package
pip install playwright

# Install browser (Chromium)
python -m playwright install chromium
```

## Step 3: Start the Services

Open 2 terminal windows and run:

**Terminal 1 - ESS Watcher** (monitors ESS every 60 seconds):
```bash
python -m ai_employee.watchers.ess_watcher
```

**Terminal 2 - Approval Executor** (executes approved actions every 30 seconds):
```bash
python -m ai_employee.approval_executor
```

## Step 4: Daily Usage

1. **Watcher detects attendance not marked** → Creates task in `vault/Needs_Action/`

2. **You review the task** → Open `vault/Needs_Action/ATTENDANCE_MARK_*.md`

3. **You approve** → Move file to `vault/Approved/`

4. **Executor marks attendance** → File moves to `vault/Done/` ✓

## Expected Output

### Watcher Terminal

```
[2026-02-07 08:15:30] Navigating to https://ess.dimionline.com/
[2026-02-07 08:15:35] Username entered
[2026-02-07 08:15:37] Login submitted and page loaded
[2026-02-07 08:15:40] Current attendance status: Unknown
[2026-02-07 08:15:42] Created attendance approval task: ATTENDANCE_MARK_20260207_*.md
```

### Executor Terminal

```
[2026-02-07 08:30:00] Executing approved action: ATTENDANCE_MARK_20260207_*.md
[2026-02-07 08:30:15] ✓ Attendance marked: Attendance marked as Present for 2026-02-07
[2026-02-07 08:30:16] ✓ Moved to Done: ATTENDANCE_MARK_20260207_*.md
```

## File Structure

```
vault/
├── Needs_Action/
│   └── ATTENDANCE_MARK_20260207_*.md  ← New! Review & approve
├── Approved/
│   └── [Move files here to approve]
├── Done/
│   └── [Completed attendance markings]
├── Rejected/
│   └── [Failed markings - needs manual action]
└── Logs/
    ├── ess_watcher.log                ← Watcher logs
    └── approval_executor.log          ← Executor logs
```

## Testing

### Test 1: Run Watcher Once (No Continuous Loop)

```bash
python -m ai_employee.watchers.ess_watcher --once
```

This will:
- Check attendance status
- Create task if needed
- Exit immediately
- Useful for testing before running continuously

### Test 2: Check Login Works

```bash
python -m ai_employee.watchers.ess_watcher --once --headless false
```

This opens a visible browser so you can see what's happening during login.

### Test 3: Run Executor Once

```bash
python -m ai_employee.approval_executor --once
```

This processes any files in `vault/Approved/` and exits.

## Troubleshooting

### Login Fails

```bash
# Try with visible browser to see what's happening
python -m ai_employee.watchers.ess_watcher --once --headless false
```

### Attendance Not Marked

```bash
# Check executor logs
tail -20 vault/Logs/approval_executor.log

# Verify file was moved to /Approved correctly
ls -la vault/Approved/

# Try executor once to see error
python -m ai_employee.approval_executor --once
```

### Watcher Crashes

```bash
# Check watcher logs for errors
tail -50 vault/Logs/ess_watcher.log

# Test once to see full error output
python -m ai_employee.watchers.ess_watcher --once
```

## Production Setup (Always Running)

For 24/7 operation, use PM2:

```bash
# Install PM2 globally
npm install -g pm2

# Start watcher
pm2 start "python -m ai_employee.watchers.ess_watcher" --name ess-watcher

# Start executor
pm2 start "python -m ai_employee.approval_executor" --name attendance-executor

# Save and auto-start on reboot
pm2 save && pm2 startup
```

Check status:
```bash
pm2 status
pm2 logs ess-watcher
pm2 logs attendance-executor
```

## Manual Marking (If Automation Fails)

If the automated marking fails and you need to mark attendance manually:

1. Go to: https://ess.dimionline.com/
2. Login with your credentials
3. Navigate to Attendance section
4. Click "Mark Present" or "Mark Attendance"
5. Select today's date
6. Confirm

## Next Steps

For full documentation, see:
- `docs/ESS_ATTENDANCE_FEATURE.md` - Complete guide with all options
- `Personal_AI_Employee_Hackathon_0_Building_Autonomous_FTEs_in_2026.md` - Overall architecture

## Key Points

✅ **Secure**: Credentials stored locally, never shared
✅ **Safe**: Human approval required (move file to approve)
✅ **Logged**: All actions recorded for audit trail
✅ **Local-first**: Runs on your machine, no cloud sync needed
✅ **Fallback**: Manual marking available if automation fails

---

**Questions?** Check `docs/ESS_ATTENDANCE_FEATURE.md` or the logs in `vault/Logs/`
