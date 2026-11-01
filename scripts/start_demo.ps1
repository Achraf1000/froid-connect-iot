$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
& "$PSScriptRoot\start.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Les services locaux ne sont pas disponibles.' }
$taskRunning = $false
if (Test-Path -LiteralPath '.runtime\presentation.json') {
    $taskStatus = Get-Content -LiteralPath '.runtime\presentation.json' -Raw | ConvertFrom-Json
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskStatus.pid)" -ErrorAction SilentlyContinue
    $taskRunning = $taskStatus.running -and $taskProcess -and $taskProcess.CommandLine.Contains("$taskRoot\scripts\presentation.py")
}
if (-not $taskRunning) {
    $taskProcess = Start-Process -FilePath "$taskRoot\.venv\Scripts\python.exe" `
        -ArgumentList @('-u',"$taskRoot\scripts\presentation.py",'--duration','1800') `
        -WorkingDirectory $taskRoot -WindowStyle Hidden `
        -RedirectStandardOutput '.runtime\presentation.out.log' `
        -RedirectStandardError '.runtime\presentation.err.log' -PassThru
    $taskDeadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 300
        if ($taskProcess.HasExited) { throw 'La demonstration a echoue : .runtime/presentation.err.log' }
        if (Test-Path -LiteralPath '.runtime\presentation.json') {
            $taskStatus = Get-Content -LiteralPath '.runtime\presentation.json' -Raw | ConvertFrom-Json
            $taskChild = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskStatus.pid)" -ErrorAction SilentlyContinue
            if ($taskStatus.running -and $taskChild -and ($taskStatus.pid -eq $taskProcess.Id -or $taskChild.ParentProcessId -eq $taskProcess.Id)) { break }
        }
        if ((Get-Date) -gt $taskDeadline) { throw 'Preparation trop longue : consulter .runtime/presentation.err.log' }
    } while ($true)
}
$taskServices = Get-Content -LiteralPath '.runtime\services.json' -Raw | ConvertFrom-Json
$taskServices | Add-Member -NotePropertyName 'presentation' -NotePropertyValue $taskStatus.pid -Force
$taskServices | ConvertTo-Json | Set-Content -LiteralPath '.runtime\services.json' -Encoding UTF8
Write-Host "Demonstration prete : $($taskStatus.url)"
Start-Process $taskStatus.url
