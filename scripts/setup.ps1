$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (!(Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Creation de .venv impossible.' }
}
& '.\.venv\Scripts\python.exe' scripts\bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'Preparation de Node.js impossible.' }
$taskNode = (Get-Content -LiteralPath '.tools\node-path.txt' -Raw).Trim()
$env:PATH = "$taskNode;$env:PATH"
& '.\.venv\Scripts\python.exe' -m pip install -r backend\requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation Python incomplete.' }
npm ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'Installation des outils JavaScript incomplete.' }
npm --prefix frontend ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'Installation de React incomplete.' }
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Compilation React impossible.' }
Write-Host 'Preparation terminee. Lancez scripts\start.ps1.'
