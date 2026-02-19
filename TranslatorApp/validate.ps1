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

# Activate venv if it exists
$venvActivate = Join-Path $scriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

$serverProcess = $null

if (-not $NoServer -and $BaseUrl -eq "http://localhost:5555") {
    Write-Host "Starting dev server..." -ForegroundColor Yellow
    $serverProcess = Start-Process -FilePath "python" `
        -ArgumentList "runserver.py" `
        -WorkingDirectory $scriptDir `
        -PassThru -WindowStyle Hidden

    # Wait for server to be ready
    $ready = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-WebRequest -Uri "$BaseUrl/health" -TimeoutSec 2 -ErrorAction Stop
            $ready = $true
            break
        } catch {
            # Server not ready yet
        }
    }

    if (-not $ready) {
        Write-Host "ERROR: Server did not start within 15 seconds" -ForegroundColor Red
        if ($serverProcess -and !$serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force }
        exit 1
    }
    Write-Host "Server is up." -ForegroundColor Green
}

# Run smoke tests
Write-Host ""
Write-Host "Running smoke tests..." -ForegroundColor Yellow
$env:BASE_URL = $BaseUrl

try {
    Push-Location $scriptDir
    python -m pytest tests/test_smoke.py -v --tb=short
    $testResult = $LASTEXITCODE
} finally {
    Pop-Location
    # Stop the server if we started it
    if ($serverProcess -and !$serverProcess.HasExited) {
        Write-Host ""
        Write-Host "Stopping dev server..." -ForegroundColor Yellow
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
