# validate.ps1 — Post-deploy validation for Windows / dev
#
# Usage:
#   .\validate.ps1                  # start server, run tests, stop server
#   .\validate.ps1 -NoServer        # run tests against already-running server
#   .\validate.ps1 -BaseUrl "https://kadeutsch.org"  # test remote server
#
param(
    [switch]$NoServer,
    [string]$BaseUrl = "http://localhost:5555"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== TranslatorApp Validation ===" -ForegroundColor Cyan
Write-Host "Target: $BaseUrl"
Write-Host ""

# Resolve Python executable — prefer venv, fall back to system
$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    Write-Host "Using venv Python: $pythonExe" -ForegroundColor Gray
} else {
    $pythonExe = "python"
    Write-Host "Using system Python" -ForegroundColor Gray
}

$serverProcess = $null

if (-not $NoServer -and $BaseUrl -eq "http://localhost:5555") {
    Write-Host "Starting dev server in background..." -ForegroundColor Yellow
    $serverProcess = Start-Process -FilePath $pythonExe `
        -ArgumentList "runserver.py" `
        -WorkingDirectory $scriptDir `
        -PassThru -WindowStyle Hidden

    Write-Host "  Server PID: $($serverProcess.Id)" -ForegroundColor Gray

    # Wait for server to be ready (poll /health every second)
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
            if ($resp -and $resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            # Server not ready yet — keep waiting
        }
        Write-Host "  ...waiting ($($i+1)s)" -ForegroundColor Gray
    }

    if (-not $ready) {
        Write-Host "ERROR: Server did not start within 20 seconds" -ForegroundColor Red
        if ($serverProcess -and !$serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force }
        exit 1
    }
    Write-Host "Server is ready." -ForegroundColor Green
}

# Run smoke tests
Write-Host ""
Write-Host "Running smoke tests..." -ForegroundColor Yellow
$env:BASE_URL = $BaseUrl

try {
    Push-Location $scriptDir
    & $pythonExe -m pytest tests/test_smoke.py -v --tb=short
    $testResult = $LASTEXITCODE
} finally {
    Pop-Location
    # Stop the server if we started it
    if ($serverProcess -and !$serverProcess.HasExited) {
        Write-Host ""
        Write-Host "Stopping dev server (PID: $($serverProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $serverProcess.Id -Force
    }
}

Write-Host ""
if ($testResult -eq 0) {
    Write-Host "=== ALL CHECKS PASSED ===" -ForegroundColor Green
} else {
    Write-Host "=== SOME CHECKS FAILED ===" -ForegroundColor Red
}

exit $testResult
