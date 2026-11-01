$ErrorActionPreference = 'Stop'
$ninjaRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ninjaRoot
# Check before launching a second worker or opening its log files.
$ninjaSocket = New-Object System.Net.Sockets.TcpClient
$ninjaListening = $false
try {
    $ninjaConnect = $ninjaSocket.ConnectAsync('127.0.0.1', 8000)
    $ninjaListening = $ninjaConnect.Wait(1500) -and $ninjaSocket.Connected
} catch {
    $ninjaListening = $false
} finally {
    $ninjaSocket.Dispose()
}
if ($ninjaListening) {
    $ninjaExisting = $null
    try {
        $ninjaExisting = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 5
    } catch {
        # An occupied port may belong to another app or an unresponsive server.
    }
    if ($ninjaExisting.info.title -eq 'Ninja Assistant' -and $ninjaExisting.paths.'/api/status') {
        Write-Host 'Ninja Assistant is already running. Open http://127.0.0.1:8000.'
        Write-Host 'Use your .env NINJA_TOKEN or data/access-token to connect. No second server or worker was started.'
        return
    }
    throw 'Port 8000 is occupied, but a responding Ninja Assistant could not be confirmed. Check the existing service before starting Ninja; no process was stopped.'
}
$ninjaPython = Join-Path $ninjaRoot '.venv/Scripts/python.exe'
$ninjaBackend = Join-Path $ninjaRoot 'backend'
New-Item -ItemType Directory -Force data | Out-Null
$ninjaWorker = Start-Process -FilePath $ninjaPython -ArgumentList '-m','ninja.worker' -WorkingDirectory $ninjaBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ninjaRoot 'data/worker.out.log') -RedirectStandardError (Join-Path $ninjaRoot 'data/worker.err.log') -PassThru
$ninjaControl = Start-Process -FilePath $ninjaPython -ArgumentList '-m','ninja.worker','control' -WorkingDirectory $ninjaBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ninjaRoot 'data/control-worker.out.log') -RedirectStandardError (Join-Path $ninjaRoot 'data/control-worker.err.log') -PassThru
Write-Host 'Open http://127.0.0.1:8000. Token is in .env or data/access-token. Ctrl+C stops the server and worker.'
try {
    Push-Location $ninjaBackend
    & $ninjaPython -m uvicorn ninja.api:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
    if ($ninjaControl -and -not $ninjaControl.HasExited) { & "$env:SystemRoot/System32/taskkill.exe" /PID $ninjaControl.Id /T /F | Out-Null }
    if (-not $ninjaWorker.HasExited) { & "$env:SystemRoot/System32/taskkill.exe" /PID $ninjaWorker.Id /T /F | Out-Null }
    # Backup for a server that did not shut down cleanly: give Qwen's GPU memory back.
    Push-Location $ninjaBackend
    & $ninjaPython -c 'from ninja import adapters; adapters.release_local_model()' 2>$null
    Pop-Location
}
