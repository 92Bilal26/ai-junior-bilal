const year = document.getElementById("year");
const themeToggle = document.getElementById("theme-toggle");
const startDemo = document.getElementById("start-demo");
const openQueue = document.getElementById("open-queue");

year.textContent = new Date().getFullYear();

let lightMode = false;

function setTheme() {
  document.body.style.background = lightMode
    ? "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)"
    : "";
  document.body.style.color = lightMode ? "#0f172a" : "";
  themeToggle.textContent = lightMode ? "Dark" : "Light";
}

themeToggle.addEventListener("click", () => {
  lightMode = !lightMode;
  setTheme();
});

startDemo.addEventListener("click", () => {
  startDemo.textContent = "Demo queued";
});

openQueue.addEventListener("click", () => {
  openQueue.textContent = "Queued tasks opened";
});

setTheme();
