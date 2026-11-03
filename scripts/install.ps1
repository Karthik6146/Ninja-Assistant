# One-click install for the release zip ("Install Ninja.cmd" runs this). Installs Python 3.11 with winget if it is
# missing, sets up Ninja, adds the Desktop and Start-menu shortcuts and opens Ninja, whose setup wizard then checks
# the PC and installs Ollama, a model and voice. Safe to run again: finished steps are skipped.
$ErrorActionPreference = 'Stop'
$ninjaRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ninjaRoot

function Find-Python {
    $known = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path $known) { return $known }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3.11 -c 'import sys;print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim() }
    }
    return $null
}

Write-Host '1/3  Python 3.11'
$python = Find-Python
if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'winget is missing. Install Python 3.11 from python.org, then run Install Ninja again.' }
    Write-Host '     Installing Python 3.11 with winget (accepts its license)...'
    winget install --id Python.Python.3.11 -e --scope user --silent --accept-source-agreements --accept-package-agreements
    $python = Find-Python
    if (-not $python) { throw 'Python 3.11 did not install. Install it from python.org, then run Install Ninja again.' }
}

Write-Host '2/3  Ninja (Python packages; a few minutes the first time)'
& (Join-Path $PSScriptRoot 'setup.ps1') -Python $python

Write-Host '3/3  Shortcuts'
& (Join-Path $PSScriptRoot 'install-app.ps1')

Write-Host 'Done. Opening Ninja; its setup wizard installs Ollama and a model that fits this PC.'
Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',"`"$(Join-Path $PSScriptRoot 'ninja-app.ps1')`"" -WindowStyle Hidden
