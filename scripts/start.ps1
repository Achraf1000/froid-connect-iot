param([switch]$Tunnel)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskNode = (Get-Content -LiteralPath '.tools\node-path.txt' -Raw).Trim()
$env:PATH = "$taskNode;$env:PATH"
New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null

function Test-LocalPort([int]$Port) {
    $taskSocket = New-Object System.Net.Sockets.TcpClient
    try {
        $taskConnect = $taskSocket.ConnectAsync('127.0.0.1', $Port)
        if (-not $taskConnect.Wait(800)) { return $false }
        return $taskSocket.Connected
    } catch { return $false }
    finally { $taskSocket.Dispose() }
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

function Wait-LocalPort([int]$Port, [string]$Name) {
    $taskDeadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $taskDeadline) {
        if (Test-LocalPort $Port) { return }
        Start-Sleep -Seconds 1
    }
    throw "$Name ne repond pas sur le port $Port. Consulter les journaux .runtime."
}

function Test-DockerReady {
    try {
        docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

if (-not (Test-DockerReady)) {
    $taskDockerExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $taskDockerExe)) {
        throw 'Docker Desktop est requis. Voir docs/DEMARRAGE_RAPIDE.md.'
    }
    Write-Host 'Demarrage de Docker Desktop...'
    Start-Process -FilePath $taskDockerExe -WindowStyle Hidden
    $taskDockerDeadline = (Get-Date).AddSeconds(90)
    while (-not (Test-DockerReady)) {
        if ((Get-Date) -gt $taskDockerDeadline) { throw 'Docker Desktop ne repond pas encore. Ouvrez-le, puis relancez.' }
        Start-Sleep -Seconds 2
    }
}

docker compose up -d mongo
if ($LASTEXITCODE -ne 0) { throw 'Demarrez Docker Desktop, puis relancez ce script.' }
Start-ProjectService 'firebase' "$taskNode\node.exe" @('node_modules/firebase-tools/lib/bin/firebase.js','emulators:start','--only','database,auth','--project','demo-cold-chain') 9000
Start-ProjectService 'api' "$taskRoot\.venv\Scripts\python.exe" @('-m','uvicorn','app.main:create_app','--factory','--app-dir','backend','--host','127.0.0.1','--port','8000') 8000
if ($Tunnel) {
    $taskNgrok = (Get-Command ngrok -ErrorAction Stop).Source
    Start-ProjectService 'ngrok' $taskNgrok @('http','http://127.0.0.1:8000','--log=stdout','--log-format=json') 4040
}
Wait-LocalPort 27018 'MongoDB'
Wait-LocalPort 9000 'Firebase Database'
Wait-LocalPort 9099 'Firebase Authentication'
Wait-LocalPort 4000 'Interface Firebase'
Wait-LocalPort 8000 'API'
if ($Tunnel) {
    Wait-LocalPort 4040 'ngrok'
    & "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\scripts\configure_wokwi.py"
    if ($LASTEXITCODE -ne 0) { throw 'Preparation Wokwi impossible. Consulter .runtime/ngrok.err.log.' }
}
& "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\scripts\local_access.py"
Write-Host 'Tableau de bord : http://127.0.0.1:8000'
Write-Host 'Interface Firebase locale : http://127.0.0.1:4000/database/demo-cold-chain-default-rtdb/data'
Write-Host 'Mot de passe : .runtime\acces-local.txt'
Write-Host 'Journaux : .runtime\api.err.log et .runtime\firebase.out.log'
