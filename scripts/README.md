# Scripts

## create-app.ps1
Creates a new app folder under `apps/<language>/<name>` and optionally runs a scaffold command.

Example:
```powershell
.\scripts\create-app.ps1 -Language laravel -Name billing-api
```

With scaffold:
```powershell
.\scripts\create-app.ps1 -Language react -Name web-portal -Command "npx create-vite@latest . -- --template react"
```
