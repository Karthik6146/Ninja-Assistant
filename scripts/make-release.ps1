# Builds release/Ninja-<version>.zip for a GitHub Release: the files git tracks (or would track), minus tests, plus
# the built UI so users need no Node. Never includes data/, .env, .venv or anything .gitignore excludes.
# Publishing stays manual: this prints the gh command to run.
param([Parameter(Mandatory)][ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version)
$ErrorActionPreference = 'Stop'
$ninjaRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ninjaRoot

Push-Location frontend
# npm writes warnings to stderr, which Windows PowerShell 5.1 turns into terminating errors; the exit code decides.
$ErrorActionPreference = 'Continue'
try { npm run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' } } finally { Pop-Location; $ErrorActionPreference = 'Stop' }

$out = Join-Path $ninjaRoot 'release'
$stage = Join-Path $out "stage\Ninja"
if (Test-Path (Join-Path $out 'stage')) { Remove-Item (Join-Path $out 'stage') -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

$files = git ls-files -co --exclude-standard | Where-Object { $_ -notmatch '^(tests/|site/|\.github/|pytest\.ini$)' }
$files += Get-ChildItem frontend/dist -Recurse -File | ForEach-Object { $_.FullName.Substring($ninjaRoot.Length + 1).Replace('\', '/') }
foreach ($file in $files) {
    $target = Join-Path $stage $file
    New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $ninjaRoot $file) -Destination $target
}
foreach ($private in '.env', 'data', '.venv') { if (Test-Path (Join-Path $stage $private)) { throw "$private reached the release folder; check .gitignore" } }

$zip = Join-Path $out "Ninja-$Version.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $stage -DestinationPath $zip
Remove-Item (Join-Path $out 'stage') -Recurse -Force

$notes = Join-Path $out "notes-$Version.md"
@"
## Ninja $Version

Jarvis, a private voice and chat assistant that runs on your Windows PC with a local model. Nothing you say leaves your computer.

### Install
1. Download **Ninja-$Version.zip** below and unzip it anywhere, for example ``Documents\Ninja``.
2. Double-click **Install Ninja**. It installs Python 3.11 if needed, sets up Ninja and adds a **Ninja** shortcut.
3. Ninja opens a setup wizard that checks your PC (memory, GPU, disk), recommends a model that fits, and installs Ollama, the model and optional voice for you.

Needs Windows 10 or 11 with winget. An NVIDIA GPU with 6 GB or more is recommended; without one, models run slower on the CPU.

### Use
Open **Ninja** from the Desktop or Start menu. It lives in the notification area: closing the window keeps it running; right-click the tray icon to quit.
"@ | Set-Content -Path $notes -Encoding utf8

$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Built $zip ($size MB, $($files.Count) files) and $notes"
Write-Host 'Publish after committing and pushing:'
Write-Host "  gh release create v$Version `"release/Ninja-$Version.zip`" --title `"Ninja $Version`" --notes-file `"release/notes-$Version.md`""
