$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExecutable = (Get-Command python -ErrorAction Stop).Source
$logDirectory = Join-Path $projectDirectory "data\logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$logPath = Join-Path $logDirectory "painel.log"

$portInUse = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    exit 0
}

Push-Location $projectDirectory
try {
    & $pythonExecutable "dashboard.py" *>> $logPath
}
finally {
    Pop-Location
}
