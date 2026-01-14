<#
.SYNOPSIS
    Setup and Run Janus API on Windows
.DESCRIPTION
    Automates the setup of Python environment, dependencies, and environment variables
    to run Janus API locally on Windows while connecting to Docker services.
#>

$ErrorActionPreference = "Stop"

# Paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$JanusDir = Join-Path $ProjectRoot "janus"
$VenvDir = Join-Path $JanusDir ".venv"

# Suppress uv hardlink warnings on Windows
$Env:UV_LINK_MODE = "copy"

Write-Host "[*] Starting Janus Setup for Windows..." -ForegroundColor Cyan
Write-Host "    Working Directory: $JanusDir" -ForegroundColor DarkGray

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.11+ and add to PATH."
}

# 2. Check/Install uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[*] 'uv' not found. Installing via pip..." -ForegroundColor Yellow
    python -m pip install uv
}

Set-Location $JanusDir

# 3. Setup Virtual Environment
if (-not (Test-Path $VenvDir)) {
    Write-Host "[*] Creating virtual environment in .venv..." -ForegroundColor Cyan
    uv venv .venv
}

# Activate venv
$VenvActivate = Join-Path $VenvDir "Scripts\activate.ps1"
if (Test-Path $VenvActivate) {
    # We invoke the activation script in the current scope
    . $VenvActivate
} else {
    Write-Error "Virtual environment activation script not found at $VenvActivate"
}

# 4. Install Dependencies
Write-Host "[*] Checking dependencies..." -ForegroundColor Cyan

# Force install key binaries for Windows compatibility
Write-Host "[*] Ensuring Windows-compatible binaries..." -ForegroundColor Yellow
uv pip install "psycopg[binary]" "asyncpg"

# Always update requirements.txt to ensure it matches pyproject.toml state
Write-Host "[*] Updating requirements from Poetry..." -ForegroundColor Yellow
uv pip install poetry poetry-plugin-export
# Try to export, but if lock file is inconsistent, just proceed to install what we can
try {
    poetry export -f requirements.txt --output requirements.txt --without-hashes 2>$null
} catch {
    Write-Host "[!] Poetry lock file might be out of sync. Proceeding with best effort..." -ForegroundColor DarkGray
}

Write-Host "[*] Installing/Syncing packages..." -ForegroundColor Cyan
# Install from requirements if available
if (Test-Path "requirements.txt") {
    uv pip install -r requirements.txt
}
# Install project in editable mode (SKIP on failure to avoid poetry build issues)
try {
    uv pip install --no-deps -e . 2>$null
} catch {
    Write-Host "[!] Editable install failed. Continuing as standard script..." -ForegroundColor DarkGray
}

# Audio Handling
try {
    python -c "import pyaudio" 2>$null
} catch {
    Write-Host "[*] PyAudio missing. Installing..." -ForegroundColor Yellow
    uv pip install pyaudio
}

# 5. Load Environment Variables
Write-Host "[*] Loading environment variables..." -ForegroundColor Cyan

function Set-EnvFromFile($Path) {
    if (Test-Path $Path) {
        Write-Host "    Loading $Path" -ForegroundColor DarkGray
        Get-Content $Path | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
            $line = $_.ToString()
            $idx = $line.IndexOf("=")
            if ($idx -gt 0) {
                $key = $line.Substring(0, $idx).Trim()
                $value = $line.Substring($idx + 1).Trim()
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
}

Set-EnvFromFile (Join-Path $JanusDir "app\.env")
Set-EnvFromFile (Join-Path $JanusDir "app\.env.windows")

# 6. Run Application
Write-Host "[+] Launching Janus API (Local)..." -ForegroundColor Green
Write-Host "    API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "    Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green

# Ensure PYTHONPATH includes the janus directory
$Env:PYTHONPATH = $JanusDir

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
