const lastSync = document.getElementById("last-sync");
const watcherStatus = document.getElementById("watcher-status");
const orchestratorStatus = document.getElementById("orchestrator-status");
const claudeStatus = document.getElementById("claude-status");
const agentStatus = document.getElementById("agent-status");
const workLog = document.getElementById("work-log");
const claudeLog = document.getElementById("claude-log");
const taskList = document.getElementById("task-list");
const approvalList = document.getElementById("approval-list");

const metricTasks = document.querySelector('[data-metric="tasks"]');
const metricApprovals = document.querySelector('[data-metric="approvals"]');

const startBtn = document.getElementById("start-watchers");
const stopBtn = document.getElementById("stop-watchers");
const runBtn = document.getElementById("run-orchestrator");
const newTaskBtn = document.getElementById("new-task");
const openVaultBtn = document.getElementById("open-vault");
const startClaudeBtn = document.getElementById("start-claude");
const stopClaudeBtn = document.getElementById("stop-claude");
const appForm = document.getElementById("app-form");
const appLanguage = document.getElementById("app-language");
const appName = document.getElementById("app-name");
const appInstruction = document.getElementById("app-instruction");
const appStatus = document.getElementById("app-status");

const state = {
  watchersRunning: false,
};

function nowLabel() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function logLine(message) {
  const p = document.createElement("p");
  p.textContent = `[${nowLabel()}] ${message}`;
  workLog.prepend(p);
}

async function fetchJSON(path, options = {}) {
  try {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!response.ok) {
      throw new Error("request failed");
    }
    return await response.json();
  } catch (error) {
    logLine(`API error: ${path}`);
    return null;
  }
}

function updateCounts(tasks = [], approvals = []) {
  metricTasks.textContent = tasks.length;
  metricApprovals.textContent = approvals.length;
}

function updateSync() {
  lastSync.textContent = nowLabel();
}

function updateWatcherState(running) {
  state.watchersRunning = running;
  watcherStatus.textContent = running ? "Running" : "Idle";
  agentStatus.textContent = running ? "Local Active" : "Local Ready";
  agentStatus.classList.toggle("online", true);
}

function renderTasks(items) {
  taskList.innerHTML = "";
  if (!items.length) {
    taskList.innerHTML = '<li class="list-item empty">No open tasks.</li>';
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML = `
      <label>
        <input type="checkbox" class="task-item" data-path="${item.path}" />
        ${item.title}
      </label>
      <span class="chip">${item.type}</span>
    `;
    taskList.appendChild(li);
  });
}

function renderApprovals(items) {
  approvalList.innerHTML = "";
  if (!items.length) {
    approvalList.innerHTML = '<li class="list-item empty">No approvals pending.</li>';
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML = `
      <div class="list-body">
        <strong>${item.title}</strong>
        <span class="chip warning">${item.type}</span>
      </div>
      <div class="list-actions">
        <button class="mini-btn approve" data-path="${item.path}">Approve</button>
        <button class="mini-btn reject" data-path="${item.path}">Reject</button>
      </div>
    `;
    approvalList.appendChild(li);
  });
}

function renderLogs(lines) {
  workLog.innerHTML = "";
  if (!lines.length) {
    workLog.innerHTML = "<p>[--:--] No logs yet.</p>";
    return;
  }
  lines
    .slice()
    .reverse()
    .forEach((line) => {
      const p = document.createElement("p");
      p.textContent = line;
      workLog.appendChild(p);
    });
}

function renderClaudeLogs(lines) {
  claudeLog.innerHTML = "";
  if (!lines.length) {
    claudeLog.innerHTML = "<p>[--:--] No Claude logs yet.</p>";
    return;
  }
  lines
    .slice()
    .reverse()
    .forEach((line) => {
      const p = document.createElement("p");
      p.textContent = line;
      claudeLog.appendChild(p);
    });
}

function setAppStatus(message, ok = true) {
  appStatus.textContent = message;
  appStatus.style.color = ok ? "var(--mint)" : "var(--accent)";
}

async function refresh() {
  const summary = await fetchJSON("/api/summary");
  const tasks = await fetchJSON("/api/tasks");
  const approvals = await fetchJSON("/api/approvals");
  const logs = await fetchJSON("/api/logs");
  const claudeLogs = await fetchJSON("/api/claude/logs");

  if (summary) {
    updateCounts(tasks?.items ?? [], approvals?.items ?? []);
    updateSync();
    claudeStatus.textContent = summary.claude_running ? "Running" : "Stopped";
  }
  if (tasks) {
    renderTasks(tasks.items);
  }
  if (approvals) {
    renderApprovals(approvals.items);
  }
  if (logs) {
    renderLogs(logs.lines);
  }
  if (claudeLogs) {
    renderClaudeLogs(claudeLogs.lines);
  }
}

startBtn.addEventListener("click", () => {
  updateWatcherState(true);
  logLine("Watchers started.");
  updateSync();
});

stopBtn.addEventListener("click", () => {
  updateWatcherState(false);
  logLine("Watchers stopped.");
  updateSync();
});

runBtn.addEventListener("click", async () => {
  orchestratorStatus.textContent = "Running";
  await fetchJSON("/api/run-orchestrator", { method: "POST", body: "{}" });
  logLine("Orchestrator executed.");
  updateSync();
  orchestratorStatus.textContent = "Ready";
  refresh();
});

newTaskBtn.addEventListener("click", async () => {
  await fetchJSON("/api/new-task", {
    method: "POST",
    body: JSON.stringify({
      title: "Draft reply for new inbound Gmail inquiry",
      type: "email",
      body: "Draft a polite reply and request approval before sending.",
    }),
  });
  logLine("New task queued.");
  refresh();
});

approvalList.addEventListener("click", async (event) => {
  const target = event.target;
  if (!target.classList.contains("mini-btn")) {
    return;
  }
  const path = target.dataset.path;
  if (!path) {
    return;
  }
  if (target.classList.contains("approve")) {
    await fetchJSON("/api/approve", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    logLine(`Approved: ${path}`);
  }
  if (target.classList.contains("reject")) {
    await fetchJSON("/api/reject", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    logLine(`Rejected: ${path}`);
  }
  refresh();
});

openVaultBtn.addEventListener("click", async () => {
  const data = await fetchJSON("/api/vault-path");
  if (data?.vault) {
    logLine(`Vault path: ${data.vault}`);
  }
});

startClaudeBtn.addEventListener("click", async () => {
  const result = await fetchJSON("/api/claude/start", { method: "POST", body: "{}" });
  if (result?.ok) {
    logLine("Claude started.");
    claudeStatus.textContent = "Running";
  } else {
    logLine("Claude start failed.");
  }
});

stopClaudeBtn.addEventListener("click", async () => {
  const result = await fetchJSON("/api/claude/stop", { method: "POST", body: "{}" });
  if (result?.ok) {
    logLine("Claude stopped.");
    claudeStatus.textContent = "Stopped";
  } else {
    logLine("Claude stop failed.");
  }
});

appForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const language = appLanguage.value.trim();
  const name = appName.value.trim();
  const instruction = appInstruction.value.trim();
  if (!language || !name) {
    setAppStatus("Language and name are required.", false);
    return;
  }

  setAppStatus("Creating app...");
  const result = await fetchJSON("/api/new-claude-task", {
    method: "POST",
    body: JSON.stringify({
      language,
      name,
      instruction,
    }),
  });
  if (result?.ok) {
    setAppStatus(`Queued task: ${result.path}`);
    logLine(`Claude task queued at ${result.path}`);
    appName.value = "";
    appInstruction.value = "";
  } else {
    setAppStatus(result?.error || "Create app failed.", false);
  }
});

refresh();
updateWatcherState(false);
setInterval(refresh, 15000);
