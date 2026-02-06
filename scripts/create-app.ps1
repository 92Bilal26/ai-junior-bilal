param(
    [Parameter(Mandatory = $true)]
    [string]$Language,

    [Parameter(Mandatory = $true)]
    [string]$Name,

    [string]$Command = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$appsRoot = Join-Path $repoRoot "apps"
$languageFolder = Join-Path $appsRoot $Language.ToLower()
$appPath = Join-Path $languageFolder $Name

if (-not (Test-Path $appsRoot)) {
    New-Item -ItemType Directory -Path $appsRoot | Out-Null
}

if (-not (Test-Path $languageFolder)) {
    New-Item -ItemType Directory -Path $languageFolder | Out-Null
}

if (Test-Path $appPath) {
    Write-Error "App path already exists: $appPath"
    exit 1
}

New-Item -ItemType Directory -Path $appPath | Out-Null

if ($Command -ne "") {
    Push-Location $appPath
    try {
        Write-Host "Running scaffold command: $Command"
        Invoke-Expression $Command
    } finally {
        Pop-Location
    }
}

Write-Host "Created app folder: $appPath"
