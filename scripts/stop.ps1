param([switch]$WithMongo)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (Test-Path -LiteralPath '.runtime\services.json') {
    $taskServices = Get-Content -LiteralPath '.runtime\services.json' -Raw | ConvertFrom-Json
    foreach ($taskEntry in $taskServices.PSObject.Properties) {
        $taskPid = [int]$taskEntry.Value
        $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$taskPid" -ErrorAction SilentlyContinue
        if ($taskProcess -and ($taskProcess.CommandLine -like "*$taskRoot*" -or ($taskEntry.Name -eq 'ngrok' -and $taskProcess.CommandLine -like '*http://127.0.0.1:8000*'))) {
            taskkill.exe /PID $taskPid /T /F | Out-Null
            Write-Host "$($taskEntry.Name) arrete."
        }
    }
    '{}' | Set-Content -LiteralPath '.runtime\services.json' -Encoding UTF8
}
if ($WithMongo) { docker compose stop mongo }
