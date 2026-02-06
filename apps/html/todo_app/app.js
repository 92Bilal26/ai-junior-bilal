// DOM Elements
const todoInput = document.getElementById('todoInput');
const addBtn = document.getElementById('addBtn');
const todoList = document.getElementById('todoList');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTodos();
    addBtn.addEventListener('click', addTodo);
    todoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addTodo();
    });
});

// Add todo
function addTodo() {
    const text = todoInput.value.trim();
    if (!text) return;

    const todo = {
        id: Date.now(),
        text: text,
        completed: false
    };

    saveTodo(todo);
    renderTodo(todo);
    todoInput.value = '';
    todoInput.focus();
}

// Render single todo
function renderTodo(todo) {
    const li = document.createElement('li');
    li.className = `todo-item ${todo.completed ? 'completed' : ''}`;
    li.id = `todo-${todo.id}`;

    li.innerHTML = `
        <input
            type="checkbox"
            class="todo-checkbox"
            ${todo.completed ? 'checked' : ''}
            onchange="toggleTodo(${todo.id})"
        >
        <span class="todo-text">${escapeHtml(todo.text)}</span>
        <button class="delete-btn" onclick="deleteTodo(${todo.id})">Delete</button>
    `;

    todoList.appendChild(li);
}

// Toggle completed
function toggleTodo(id) {
    const todos = JSON.parse(localStorage.getItem('todos')) || [];
    const todo = todos.find(t => t.id === id);
    if (todo) {
        todo.completed = !todo.completed;
        localStorage.setItem('todos', JSON.stringify(todos));

        const el = document.getElementById(`todo-${id}`);
        el.classList.toggle('completed');
    }
}

// Delete todo
function deleteTodo(id) {
    let todos = JSON.parse(localStorage.getItem('todos')) || [];
    todos = todos.filter(t => t.id !== id);
    localStorage.setItem('todos', JSON.stringify(todos));

    const el = document.getElementById(`todo-${id}`);
    el.remove();
}

// Save todo
function saveTodo(todo) {
    const todos = JSON.parse(localStorage.getItem('todos')) || [];
    todos.push(todo);
    localStorage.setItem('todos', JSON.stringify(todos));
}

// Load todos
function loadTodos() {
    const todos = JSON.parse(localStorage.getItem('todos')) || [];
    todos.forEach(todo => renderTodo(todo));
}

// Escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
