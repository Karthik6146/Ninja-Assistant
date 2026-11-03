param([string]$Python)  # A python.exe to build .venv with; default is the py launcher's 3.11.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv/Scripts/python.exe)) {
    if ($Python) { & $Python -m venv .venv } else { py -3.11 -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 first' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
# The release zip ships the built UI; a git clone builds it, which needs Node 22+.
if (-not (Test-Path frontend/dist/index.html)) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Install Node 22+ to build the UI, or use the release zip, which includes it' }
    Push-Location frontend
    try {
        npm ci --ignore-scripts
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Setup complete. Leave NINJA_TOKEN blank in .env to generate data/access-token. Video tools need ffmpeg/ffprobe on PATH.'
