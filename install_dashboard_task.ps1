$ErrorActionPreference = "Stop"
$taskName = "DMB - Painel WhatsApp"
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $projectDirectory "start_dashboard.ps1"
$powershellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction `
    -Execute $powershellExecutable `
    -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runnerPath`"" `
    -WorkingDirectory $projectDirectory
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Inicia o painel local de gestão dos envios do Robô DMB."

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Write-Output "Tarefa '$taskName' registrada para iniciar no logon de $currentUser."
