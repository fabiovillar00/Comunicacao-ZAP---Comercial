$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDirectory = Join-Path $projectDirectory "data\logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDirectory "execucao-$timestamp.log"
$pythonExecutable = (Get-Command python -ErrorAction Stop).Source

Push-Location $projectDirectory
try {
    & $pythonExecutable "app.py" "--run-once" *>&1 | Tee-Object -FilePath $logPath
    exit $LASTEXITCODE
}
catch {
    $_ | Out-String | Tee-Object -FilePath $logPath -Append
    exit 1
}
finally {
    Pop-Location
}
