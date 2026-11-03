# One-click install for the release zip ("Install Ninja.cmd" runs this). Checks and installs everything Ninja needs:
# Python 3.11, Ninja's packages, Ollama, the model that fits this PC, the voice models, and the Desktop and
# Start-menu shortcuts. Then opens Ninja. Nothing needs winget: installers are downloaded from python.org and
# ollama.com when missing. Safe to run again: finished steps are skipped.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # Invoke-WebRequest's progress bar makes downloads many times slower.
$env:PYTHONWARNINGS = 'ignore'  # Library warnings would look like errors to the person installing.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ninjaRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ninjaRoot
$downloads = Join-Path $env:TEMP 'ninja-setup'
New-Item -ItemType Directory -Force $downloads | Out-Null

function Get-Installer($name, $url) {
    $file = Join-Path $downloads $name
    if (-not (Test-Path $file)) {
        Write-Host "     Downloading $name..."
        Invoke-WebRequest -Uri $url -OutFile "$file.partial" -UseBasicParsing
        Move-Item "$file.partial" $file -Force
    }
    # Only a file signed by its publisher runs; a damaged or tampered download is deleted.
    $signature = Get-AuthenticodeSignature $file
    if ($signature.Status -ne 'Valid') { Remove-Item $file; throw "$name is not correctly signed ($($signature.Status)). Check the internet connection, then run Install Ninja again." }
    return $file
}

function Find-Python {
    $known = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path $known) { return $known }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3.11 -c 'import sys;print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim() }
    }
    return $null
}

function Find-Ollama {
    $found = Get-Command ollama -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $known = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path $known) { return $known }
    return $null
}

function Test-Ollama { try { (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3) -ne $null } catch { $false } }

Write-Host '1/6  Python 3.11'
$python = Find-Python
if (-not $python) {
    # The official installer, per user, no admin prompt. 3.11.9 is the last 3.11 with a Windows installer.
    $setup = Get-Installer 'python-3.11.9-amd64.exe' 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    Write-Host '     Installing Python 3.11 (a minute)...'
    $done = Start-Process -FilePath $setup -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_test=0','Include_launcher=1' -Wait -PassThru
    $python = Find-Python
    if (-not $python) { throw "Python 3.11 did not install (installer code $($done.ExitCode)). Install it from python.org/downloads, then run Install Ninja again." }
}
Write-Host "     $python"

Write-Host '2/6  Ninja (Python packages; a few minutes the first time)'
& (Join-Path $PSScriptRoot 'setup.ps1') -Python $python
$venv = Join-Path $ninjaRoot '.venv\Scripts\python.exe'
$backend = Join-Path $ninjaRoot 'backend'

Write-Host '3/6  Ollama (runs the AI model)'
$ollama = Find-Ollama
if (-not $ollama) {
    $setup = Get-Installer 'OllamaSetup.exe' 'https://ollama.com/download/OllamaSetup.exe'
    Write-Host '     Installing Ollama...'
    Start-Process -FilePath $setup -ArgumentList '/VERYSILENT','/SP-','/NORESTART' -Wait
    $ollama = Find-Ollama
    if (-not $ollama) { throw 'Ollama did not install. Install it from ollama.com/download, then run Install Ninja again.' }
}
if (-not (Test-Ollama)) {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-Ollama)) {
        if ((Get-Date) -gt $deadline) { throw 'Ollama is installed but did not start. Open Ollama from the Start menu, then run Install Ninja again.' }
        Start-Sleep -Seconds 1
    }
}
Write-Host "     $ollama"

Write-Host '4/6  AI model'
# The same choice the in-app wizard makes: the largest Qwen that fits this PC's GPU, or RAM without one.
Push-Location $backend
try {
    # Python reads these from stdin: Windows PowerShell mangles quotes inside a -c argument.
    $model = (@'
from ninja.setup_routes import system,fit
print(fit(system())[1] or '')
'@ | & $venv -).Trim()
    if (-not $model) { throw 'This PC has too little memory or disk for any model. Free disk space, then run Install Ninja again.' }
    $installed = @'
from ninja.setup_routes import ollama_state
for name in ollama_state()['models']:print(name)
'@ | & $venv -
    if ($installed -contains $model) { Write-Host "     $model is installed" }
    else {
        Write-Host "     Downloading $model (one time; size depends on your PC)..."
        & $ollama pull $model
        if ($LASTEXITCODE -ne 0) { throw "Could not download $model. Check the internet connection, then run Install Ninja again." }
    }
    @"
from ninja import db
with db.connect() as c:
    c.execute("INSERT OR REPLACE INTO preferences VALUES('chat_provider','ollama')")
    c.execute("INSERT OR REPLACE INTO preferences VALUES('ollama_model',?)",('$model',))
"@ | & $venv -
    if ($LASTEXITCODE -ne 0) { throw "Could not select $model for Jarvis." }
} finally { Pop-Location }

Write-Host '5/6  Voice (speech models; about 1.5 GB, plus NVIDIA libraries on a GPU PC)'
$voice = Join-Path $ninjaRoot 'data\services\jarvis-voice\models'
if ((Test-Path (Join-Path $voice 'kokoro-v1.0.onnx')) -and (Test-Path (Join-Path $voice 'listener\hey_jarvis_v0.1.onnx'))) { Write-Host '     Voice is installed' }
else {
    & $venv (Join-Path $PSScriptRoot 'setup-local-voice.py') --project $ninjaRoot
    if ($LASTEXITCODE -ne 0) { Write-Host '     Voice setup did not finish; Ninja still works by typing. Set up voice later from Settings.' }
}

Write-Host '6/6  Shortcuts'
& (Join-Path $PSScriptRoot 'install-app.ps1')

Write-Host 'Done. Opening Ninja.'
Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',"`"$(Join-Path $PSScriptRoot 'ninja-app.ps1')`"" -WindowStyle Hidden
