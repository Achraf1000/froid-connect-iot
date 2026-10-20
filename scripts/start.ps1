param([switch]$Tunnel)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskNode = (Get-Content -LiteralPath '.tools\node-path.txt' -Raw).Trim()
$env:PATH = "$taskNode;$env:PATH"
New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null

function Test-LocalPort([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

$taskServices = @{}
if (Test-Path -LiteralPath '.runtime\services.json') {
    $taskExisting = Get-Content -LiteralPath '.runtime\services.json' -Raw | ConvertFrom-Json
    foreach ($taskProperty in $taskExisting.PSObject.Properties) {
        $taskServices[$taskProperty.Name] = $taskProperty.Value
    }
}

function Start-ProjectService([string]$Name, [string]$Executable, [string[]]$Arguments, [int]$Port) {
    if (Test-LocalPort $Port) {
        Write-Host "$Name : port $Port deja disponible."
        return
    }
    $taskProcess = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WorkingDirectory $taskRoot -WindowStyle Hidden `
        -RedirectStandardOutput ".runtime\$Name.out.log" `
        -RedirectStandardError ".runtime\$Name.err.log" -PassThru
    $taskServices[$Name] = $taskProcess.Id
    $taskServices | ConvertTo-Json | Set-Content -LiteralPath '.runtime\services.json' -Encoding UTF8
    Write-Host "$Name : processus lance."
}

docker compose up -d mongo
if ($LASTEXITCODE -ne 0) { throw 'Demarrez Docker Desktop, puis relancez ce script.' }
Start-ProjectService 'firebase' "$taskNode\node.exe" @('node_modules/firebase-tools/lib/bin/firebase.js','emulators:start','--only','database,auth','--project','demo-cold-chain') 9000
Start-ProjectService 'api' "$taskRoot\.venv\Scripts\python.exe" @('-m','uvicorn','app.main:create_app','--factory','--app-dir','backend','--host','127.0.0.1','--port','8000') 8000
if ($Tunnel) {
    $taskNgrok = (Get-Command ngrok -ErrorAction Stop).Source
    Start-ProjectService 'ngrok' $taskNgrok @('http','http://127.0.0.1:8000','--log=stdout','--log-format=json') 4040
}
& "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\scripts\local_access.py"
Write-Host 'Tableau de bord : http://127.0.0.1:8000'
Write-Host 'Mot de passe : .runtime\acces-local.txt'
Write-Host 'Journaux : .runtime\api.err.log et .runtime\firebase.out.log'
