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
$PyprojectPath = Join-Path $JanusDir "pyproject.toml"

# Suppress uv hardlink warnings on Windows
$Env:UV_LINK_MODE = "copy"

Write-Host "[*] Starting Janus Setup for Windows..." -ForegroundColor Cyan
Write-Host "    Working Directory: $JanusDir" -ForegroundColor DarkGray

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.11+ and add to PATH."
}

# Validate project layout
if (-not (Test-Path $JanusDir)) {
    Write-Error "Janus directory not found: $JanusDir"
}

if (-not (Test-Path $PyprojectPath)) {
    Write-Error "pyproject.toml not found in: $JanusDir"
}

# Validate Python version
try {
    $pythonVersion = & python -c "import sys; print('%d.%d.%d' % sys.version_info[:3])"
    $versionParts = $pythonVersion.Trim().Split('.')
    if ($versionParts.Count -lt 2) {
        Write-Error "Unable to parse Python version: $pythonVersion"
    }
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Error "Python 3.11+ required. Found $pythonVersion."
    }
} catch {
    Write-Error "Failed to validate Python version. Ensure Python 3.11+ is installed."
}

# 2. Check/Install uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[*] 'uv' not found. Installing via pip (user scope)..." -ForegroundColor Yellow
    python -m pip install --user uv

    $userBase = & python -c "import site; print(site.USER_BASE)" 2>$null
    if ($userBase) {
        $userScripts = Join-Path $userBase "Scripts"
        if ($Env:PATH -notlike "*$userScripts*") {
            $Env:PATH = "$userScripts;$Env:PATH"
        }
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv not found on PATH after install. Restart PowerShell or add Python Scripts to PATH."
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

Write-Host "[*] Installing/Syncing packages..." -ForegroundColor Cyan
uv pip install -e .

# Audio Handling
try {
    python -c "import pyaudio" 2>$null
} catch {
    Write-Host "[!] PyAudio not available. Audio features may be disabled." -ForegroundColor Yellow
}

# 5. Load Environment Variables
Write-Host "[*] Loading environment variables..." -ForegroundColor Cyan

function Set-EnvFromFile($Path) {
    if (Test-Path $Path) {
        Write-Host "    Loading $Path" -ForegroundColor DarkGray
        Get-Content $Path | ForEach-Object {
            $line = $_.ToString().Trim()
            if (-not $line -or $line.StartsWith('#')) { return }
            if ($line.StartsWith('export ')) { $line = $line.Substring(7).Trim() }

            $idx = $line.IndexOf('=')
            if ($idx -le 0) { return }

            $key = $line.Substring(0, $idx).Trim()
            $value = $line.Substring($idx + 1).Trim()

            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            [Environment]::SetEnvironmentVariable($key, $value, "Process")
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
if ($Env:PYTHONPATH) {
    $Env:PYTHONPATH = "$JanusDir;$Env:PYTHONPATH"
} else {
    $Env:PYTHONPATH = $JanusDir
}

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
