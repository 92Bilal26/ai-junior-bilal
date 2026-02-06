# AI Employee App Workspace

This is the main workspace for all apps built by the AI employee.

## Folder layout
- `apps/laravel/` - Laravel projects
- `apps/java/` - Java (Spring Boot) projects
- `apps/react/` - React projects
- `apps/html/` - HTML/CSS/JS projects
- `apps/ai/` - AI services (Python/FastAPI/etc.)
- `apps/backend/` - Backend services (Node/Express/Nest/etc.)
- `apps/frontend/` - Frontend apps (Next/Vite/etc.)

## Create a new app
Use the helper script to create a new app folder:

```powershell
.\scripts\create-app.ps1 -Language laravel -Name billing-api
```

Optional: pass a CLI scaffold command that will run inside the new folder:

```powershell
.\scripts\create-app.ps1 -Language react -Name web-portal -Command "npx create-vite@latest . -- --template react"
```
