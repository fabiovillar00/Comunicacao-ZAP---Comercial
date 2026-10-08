$ErrorActionPreference = "Continue"
$projectDirectory = Split-Path -Parent $PSScriptRoot
$os = Get-CimInstance Win32_OperatingSystem
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
$python = Get-Command python -ErrorAction SilentlyContinue
$odbc17 = Get-OdbcDriver -Name "ODBC Driver 17 for SQL Server" -ErrorAction SilentlyContinue
$odbc18 = Get-OdbcDriver -Name "ODBC Driver 18 for SQL Server" -ErrorAction SilentlyContinue

Write-Host "Diagnóstico do SRV-APP-01" -ForegroundColor Cyan
Write-Host "Computador: $env:COMPUTERNAME"
Write-Host "Windows: $($os.Caption) $($os.Version)"
Write-Host "Usuário: $($identity.Name)"
Write-Host "Administrador: $isAdmin"
Write-Host "Python: $(if ($python) { $python.Source } else { 'NÃO INSTALADO' })"
Write-Host "ODBC 17: $([bool]$odbc17)"
Write-Host "ODBC 18: $([bool]$odbc18)"

Write-Host "`nConectividade" -ForegroundColor Cyan
foreach ($test in @(
    @{Name="SQL Server"; Host="Srv-BD-01"; Port=1433},
    @{Name="Meta API"; Host="graph.facebook.com"; Port=443}
)) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $client.BeginConnect($test.Host, $test.Port, $null, $null)
        $connected = $connection.AsyncWaitHandle.WaitOne(5000, $false)
        if ($connected) {
            $client.EndConnect($connection)
        }
    }
    catch {
        $connected = $false
    }
    finally {
        $client.Close()
    }
    Write-Host "$($test.Name) [$($test.Host):$($test.Port)]: $connected"
}

if ($python) {
    Write-Host "`nBibliotecas Python" -ForegroundColor Cyan
    & $python.Source -c "import sys; print('Versão:',sys.version); import pyodbc; print('pyodbc:',pyodbc.version)" 2>&1
}

Write-Host "`nNenhuma configuração foi alterada por este diagnóstico." -ForegroundColor Green
Read-Host "Pressione ENTER para fechar"
