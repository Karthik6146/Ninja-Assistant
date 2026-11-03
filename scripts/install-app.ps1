# Adds "Ninja" shortcuts to the Desktop and Start menu; each opens scripts/ninja-app.ps1 without a console window.
# Run again after moving the project folder. Remove the shortcuts to uninstall; nothing else is installed.
$ErrorActionPreference = 'Stop'
$ninjaRoot = Split-Path $PSScriptRoot -Parent
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
    $link = $shell.CreateShortcut((Join-Path $folder 'Ninja.lnk'))
    $link.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'ninja-app.ps1')`""
    $link.WorkingDirectory = $ninjaRoot
    $link.IconLocation = (Join-Path $ninjaRoot 'assets\ninja.ico')
    $link.Description = 'Ninja Assistant'
    $link.WindowStyle = 7  # Minimized, so the PowerShell host does not flash a window.
    $link.Save()
    Write-Host "Added $($link.FullName)"
}
