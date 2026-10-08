$ErrorActionPreference = "Stop"
$taskName = "DMB - Faturamento WhatsApp"
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $projectDirectory "run_scheduled.ps1"
$powershellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction `
    -Execute $powershellExecutable `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$runnerPath`"" `
    -WorkingDirectory $projectDirectory

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -WeeksInterval 1 `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At "18:00"
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Consulta o faturamento do dia no ERP e envia o resumo pelo WhatsApp de segunda a sexta às 18h."

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Write-Output "Tarefa '$taskName' registrada de segunda a sexta às 18:00 como $currentUser."
