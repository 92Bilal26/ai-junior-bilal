const display = document.getElementById("display");
const keys = document.getElementById("keys");
const statusLabel = document.getElementById("status");

const allowed = /^[0-9+\-*/().\s]+$/;

function setStatus(text, ok = true) {
  statusLabel.textContent = text;
  statusLabel.style.color = ok ? "var(--muted)" : "var(--danger)";
}

function append(value) {
  display.value += value;
}

function clearDisplay() {
  display.value = "";
  setStatus("Cleared");
}

function deleteLast() {
  display.value = display.value.slice(0, -1);
}

function evaluateExpression() {
  const expression = display.value.trim();
  if (!expression) {
    setStatus("Enter a value");
    return;
  }
  if (!allowed.test(expression)) {
    setStatus("Invalid characters", false);
    return;
  }
  try {
    // eslint-disable-next-line no-new-func
    const result = Function(`"use strict"; return (${expression})`)();
    display.value = Number.isFinite(result) ? String(result) : "Error";
    setStatus("Done");
  } catch (error) {
    display.value = "Error";
    setStatus("Error", false);
  }
}

keys.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const action = button.dataset.action;
  const value = button.dataset.value;

  if (action === "clear") return clearDisplay();
  if (action === "delete") return deleteLast();
  if (action === "equals") return evaluateExpression();
  if (value) append(value);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    evaluateExpression();
    return;
  }
  if (event.key === "Backspace") {
    deleteLast();
    return;
  }
  if (event.key === "Escape") {
    clearDisplay();
    return;
  }
  if (allowed.test(event.key)) {
    append(event.key);
  }
});

setStatus("Ready");
