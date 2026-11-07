param([switch]$SetupAI, [ValidateRange(1,65535)][int]$Port = 8010)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host 'Creating a private Python environment for MindVault...'
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv backend/.venv }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv backend/.venv }
    else { throw 'Python is missing. Install Python 3.12 or 3.14 and reopen this terminal.' }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
$dependencyMarker = Join-Path $PSScriptRoot 'backend/.venv/.mindvault-installed'
if (-not (Test-Path -LiteralPath $dependencyMarker)) {
    & $pythonPath -m pip install -r backend/requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the connection and retry.' }
    Set-Content -LiteralPath $dependencyMarker -Value 'requirements-lock.txt'
}
if ($SetupAI) { & $pythonPath backend/scripts/configure_local.py --ai }
else { & $pythonPath backend/scripts/configure_local.py }
if ($LASTEXITCODE -ne 0) { throw 'Local configuration failed.' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Frontend build missing. In frontend run npm ci and npm run build first.' }
Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C here to stop."
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
