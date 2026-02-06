# Auto-Execution Workflow

## Overview

The auto-execution workflow automatically executes planned Claude tasks without manual intervention. When you queue a task for Claude (like creating an HTML app), the system now:

1. **Creates** the task in `vault/Needs_Action/`
2. **Plans** it via the orchestrator (creates a checklist)
3. **Executes** it automatically via Claude
4. **Completes** it by moving to `vault/Done/` when Claude finishes

## Architecture

### Components

```
Dashboard (web UI)
    ↓
Server (dashboard/server.py)
    ├─ Orchestrator Loop → Creates plans for new tasks
    ├─ Executor Loop → Executes planned Claude tasks
    └─ Watchdog Loop → Keeps Claude running
        ↓
    Claude Runner (ai_employee/claude_runner.py)
        ↓
    Claude CLI (stdin/stdout)
```

### Flow Diagram

```
User creates task
        ↓
[Needs_Action] folder
        ↓
Orchestrator finds unplanned task
        ↓
Creates [Plans] with checklist
        ↓
Updates task status: "planned"
        ↓
Executor finds planned Claude tasks
        ↓
Sends execution prompt to Claude
        ↓
Task status: "executing"
        ↓
Claude executes (creates files, etc)
        ↓
User marks task done or executor detects completion
        ↓
Task moved to [Done]
```

## Configuration

### Environment Variables

Add these to `.env` to enable auto-execution:

```bash
# Enable automatic task execution
DASHBOARD_EXECUTOR_AUTORUN=true

# Check for executable tasks every 30 seconds
DASHBOARD_EXECUTOR_INTERVAL=30

# Keep Claude running (required for execution)
DASHBOARD_CLAUDE_AUTOSTART=true
DASHBOARD_CLAUDE_WATCHDOG=true

# Auto-run orchestrator (creates plans)
DASHBOARD_ORCHESTRATOR_AUTORUN=true
DASHBOARD_ORCHESTRATOR_INTERVAL=60
```

**Defaults:**
- `DASHBOARD_EXECUTOR_AUTORUN=false` (disabled by default)
- `DASHBOARD_EXECUTOR_INTERVAL=30` (seconds)

### Enabling Auto-Execution

1. Edit `.env` in the project root:
```bash
DASHBOARD_EXECUTOR_AUTORUN=true
DASHBOARD_CLAUDE_AUTOSTART=true
DASHBOARD_CLAUDE_WATCHDOG=true
DASHBOARD_ORCHESTRATOR_AUTORUN=true
```

2. Restart the dashboard server:
```bash
python dashboard/server.py
```

## Task Types

The executor automatically executes tasks with these types:

- `claude_app` - Scaffold new applications (HTML, React, etc)
- `claude_task` - General Claude tasks
- `claude_code` - Code generation/modification tasks

Other task types (like `email`, `file_drop`, `git`) require manual approval in the dashboard.

## Status Flow

### Task Status Values

```
new → planned → executing → done
                    ↓
                  (optional: failed if retried)
```

**New**: Task just created, needs planning
**Planned**: Orchestrator created execution plan, ready for Claude
**Executing**: Executor sent task to Claude, awaiting completion
**Done**: Claude completed the task, files created/modified

## Monitoring

### Check Auto-Execution Status

Run the test script:
```bash
python scripts/test-auto-execution.py
```

Output shows:
- How many executable tasks exist
- Workflow status (tasks in each folder)
- Task properties (type, status, instruction)

### View Logs

```bash
# Task executor logs
tail -f vault/Logs/task_executor.log

# Claude execution logs
tail -f vault/Logs/claude_cli.log

# Dashboard logs
tail -f vault/Logs/dashboard.log
```

### Dashboard API Endpoints

Check status via HTTP:
```bash
# Get Claude status
curl http://localhost:8787/api/claude/status

# Get task summary
curl http://localhost:8787/api/summary

# Get all tasks
curl http://localhost:8787/api/tasks
```

## Example Workflow

### Step 1: Create Task via Dashboard

```javascript
// User submits form on dashboard
Language: html
Name: calculator
Instruction: create a small calculator with js and css
```

Creates: `vault/Needs_Action/TASK_scaffold_html_app_calculator_[timestamp].md`

### Step 2: Orchestrator Plans Task (1 minute)

Orchestrator loop runs every 60 seconds:
- Finds unplanned tasks in `Needs_Action/`
- Creates plan checklist in `Plans/`
- Updates task status to "planned"

Creates: `vault/Plans/PLAN_scaffold_html_app_calculator_[timestamp].md`

### Step 3: Executor Executes Task (30 seconds)

Executor loop runs every 30 seconds:
- Finds planned Claude-type tasks
- Updates task status to "executing"
- Sends execution prompt to Claude
- Claude processes and creates files

### Step 4: Claude Completes (variable time)

Claude receives prompt and:
1. Reads the task instruction
2. Creates app structure in `apps/html/calculator/`
3. Implements index.html, styles.css, app.js
4. Updates task status to done

Files created: `apps/html/calculator/` with full implementation

### Step 5: Task Complete

Task moved to: `vault/Done/TASK_scaffold_html_app_calculator_[timestamp].md`

## Troubleshooting

### No Tasks Auto-Executing

1. **Check configuration**:
   ```bash
   grep DASHBOARD_EXECUTOR .env
   # Should show: DASHBOARD_EXECUTOR_AUTORUN=true
   ```

2. **Verify Claude is running**:
   ```bash
   ps aux | grep claude
   # Or check dashboard: Claude Status should be "Running"
   ```

3. **Check logs**:
   ```bash
   tail -20 vault/Logs/task_executor.log
   tail -20 vault/Logs/claude_cli.log
   ```

4. **Verify task structure**:
   ```bash
   python scripts/test-auto-execution.py
   # Should show executable tasks in output
   ```

### Tasks Stuck in "Executing"

1. Claude may have crashed - restart via dashboard
2. Check `vault/Logs/claude_cli.log` for errors
3. Manually move task to `Done/` if Claude finished

### Executor Not Running

1. Verify `DASHBOARD_EXECUTOR_AUTORUN=true` in `.env`
2. Check if dashboard server is running
3. Restart dashboard: `python dashboard/server.py`

## API Reference

### Task Executor Functions

```python
from ai_employee.claude_task_executor import (
    find_executable_tasks,      # Find planned Claude tasks
    execute_task,               # Execute single task
    process_executable_tasks,   # Batch execute all executable tasks
    mark_task_done,             # Move task to Done folder
)
```

### Manual Execution

Force immediate execution without waiting for interval:

```bash
# Run orchestrator (plan new tasks)
curl -X POST http://localhost:8787/api/run-orchestrator

# To manually execute tasks via dashboard, create endpoint
# (future enhancement)
```

## Performance

- **Executor interval**: 30 seconds (default)
- **Orchestrator interval**: 60 seconds (default)
- **Overhead**: < 100ms per cycle on modern systems
- **Concurrency**: Single-threaded, tasks executed sequentially

## Security Considerations

1. **Task types**: Only whitelisted types (`claude_app`, `claude_task`, `claude_code`) are auto-executed
2. **Approval types** (`email`, `git_push`, `payment`, `social`) require manual approval
3. **Execution context**: Tasks run with same permissions as Claude CLI process
4. **Input validation**: All task files are validated for proper structure

## Future Enhancements

- [ ] Parallel task execution (run multiple tasks simultaneously)
- [ ] Task priority/queueing system
- [ ] Failure recovery and retry logic
- [ ] Completion detection (detect when Claude finishes automatically)
- [ ] Result streaming (display Claude output in real-time)
- [ ] Task cancellation support
