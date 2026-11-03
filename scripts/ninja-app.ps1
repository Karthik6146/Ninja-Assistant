# Ninja as a desktop app with a tray icon: starts the server if needed, opens its own Edge app window signed in with
# a one-time code, and stays in the notification area. Closing the window keeps Ninja running in the background;
# "Quit Ninja" in the tray menu stops the server and workers, but only if this tray started them.
# -Background starts the tray and server without opening the window (used by "Start with Windows").
param([switch]$Background)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$ninjaRoot = Split-Path $PSScriptRoot -Parent
$url = 'http://127.0.0.1:8000'
$script:server = $null

# Dark menu in the app's graphite palette, with a cyan check mark (Jarvis's colour).
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing -TypeDefinition @'
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
public class NinjaColors : ProfessionalColorTable {
    static readonly Color Surface = Color.FromArgb(22, 22, 24), Hover = Color.FromArgb(39, 39, 42), Line = Color.FromArgb(38, 38, 41), Edge = Color.FromArgb(54, 54, 58);
    public override Color ToolStripDropDownBackground { get { return Surface; } }
    public override Color ImageMarginGradientBegin { get { return Surface; } }
    public override Color ImageMarginGradientMiddle { get { return Surface; } }
    public override Color ImageMarginGradientEnd { get { return Surface; } }
    public override Color MenuBorder { get { return Edge; } }
    public override Color MenuItemBorder { get { return Hover; } }
    public override Color MenuItemSelected { get { return Hover; } }
    public override Color MenuItemSelectedGradientBegin { get { return Hover; } }
    public override Color MenuItemSelectedGradientEnd { get { return Hover; } }
    public override Color SeparatorDark { get { return Line; } }
    public override Color SeparatorLight { get { return Surface; } }
    public override Color CheckBackground { get { return Surface; } }
    public override Color CheckSelectedBackground { get { return Hover; } }
    public override Color CheckPressedBackground { get { return Hover; } }
}
public class NinjaRenderer : ToolStripProfessionalRenderer {
    public NinjaRenderer() : base(new NinjaColors()) { RoundedEdges = false; }
    // Keep each item's own colour, also for the greyed-out status rows.
    // The base renderer greys disabled text, which lost the green or red status dot.
    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e) {
        if (e.Item.Enabled) { e.TextColor = e.Item.ForeColor; base.OnRenderItemText(e); return; }
        TextRenderer.DrawText(e.Graphics, e.Text, e.TextFont, e.TextRectangle, e.Item.ForeColor, e.TextFormat);
    }
    protected override void OnRenderItemCheck(ToolStripItemImageRenderEventArgs e) {
        Rectangle r = e.ImageRectangle;
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        using (Pen pen = new Pen(Color.FromArgb(60, 207, 242), 2f)) {
            e.Graphics.DrawLines(pen, new Point[] { new Point(r.Left + 3, r.Top + r.Height / 2), new Point(r.Left + r.Width / 2 - 1, r.Bottom - 4), new Point(r.Right - 3, r.Top + 4) });
        }
    }
}
'@

function Test-Ninja {
    try { return (Invoke-RestMethod -Uri "$url/openapi.json" -TimeoutSec 2).info.title -eq 'Ninja Assistant' } catch { return $false }
}

function Start-Ninja {
    if (Test-Ninja) { return $true }
    $script:server = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'start.ps1') -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(90)
    while (-not (Test-Ninja)) {
        if ($script:server.HasExited -or (Get-Date) -gt $deadline) {
            if (-not $script:server.HasExited) { & "$env:SystemRoot/System32/taskkill.exe" /PID $script:server.Id /T /F | Out-Null }
            $script:server = $null
            [System.Windows.Forms.MessageBox]::Show("Ninja's server did not start. Run scripts/start.ps1 in a terminal to see why.", 'Ninja') | Out-Null
            return $false
        }
        Start-Sleep -Milliseconds 500
    }
    return $true
}

function Stop-Ninja {
    if ($script:server -and -not $script:server.HasExited) { & "$env:SystemRoot/System32/taskkill.exe" /PID $script:server.Id /T /F | Out-Null }
    $script:server = $null
}

# Same order as ninja.config: the NINJA_TOKEN environment variable, then .env, then data/access-token. Used only in
# request headers to this PC's server; never shown.
function Get-NinjaToken {
    if ($env:NINJA_TOKEN) { return $env:NINJA_TOKEN }
    $envFile = Join-Path $ninjaRoot '.env'
    if (Test-Path $envFile) {
        $line = Select-String -Path $envFile -Pattern '^\s*NINJA_TOKEN\s*=(.*)$' | Select-Object -First 1
        # An empty NINJA_TOKEN= line falls through to the file, as it does for the server.
        if ($line) { $value = $line.Matches[0].Groups[1].Value.Trim().Trim('"', "'"); if ($value) { return $value } }
    }
    return (Get-Content (Join-Path $ninjaRoot 'data/access-token') -Raw).Trim()
}

function Invoke-Ninja($path, $method = 'GET', $body = $null) {
    $headers = @{ 'X-Ninja-Token' = (Get-NinjaToken) }
    if ($body) { return Invoke-RestMethod -Uri "$url/api$path" -Method $method -Headers $headers -ContentType 'application/json' -Body ($body | ConvertTo-Json) -TimeoutSec 10 }
    return Invoke-RestMethod -Uri "$url/api$path" -Method $method -Headers $headers -TimeoutSec 5
}

# Brings an open Ninja window forward, or opens a new one signed in with a fresh one-time code.
function Open-Ninja {
    # Edge's first process hands the window to a browser process and exits, so look for the app profile's browser
    # process (the one without --type=); AppActivate is false when it has no window left, and a new one opens.
    $browser = Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like '*app-window*' -and $_.CommandLine -notlike '*--type=*' } | Select-Object -First 1
    if ($browser -and (New-Object -ComObject WScript.Shell).AppActivate([int]$browser.ProcessId)) { return }
    if (-not (Start-Ninja)) { return }
    # The server deletes the code on first use and refuses it after two minutes.
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $code = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
    Set-Content -Path (Join-Path $ninjaRoot 'data/launch-code') -Value $code -NoNewline -Encoding ascii
    $edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edge) { Start-Process "$url/#launch=$code"; return }  # No Edge: the default browser still signs in.
    # Its own profile keeps the window a separate browser process (found above to focus it), with its own microphone
    # permission and sign-in apart from everyday browsing.
    Start-Process -FilePath $edge -ArgumentList "--app=$url/#launch=$code", "--user-data-dir=`"$(Join-Path $ninjaRoot 'data/app-window')`"", '--no-first-run', '--window-size=1280,860' | Out-Null
}

# "Start with Windows" is a shortcut in the user's Startup folder that runs this tray with -Background.
$startupLink = Join-Path ([Environment]::GetFolderPath('Startup')) 'Ninja.lnk'
function Set-Startup($on) {
    if (-not $on) { Remove-Item $startupLink -ErrorAction SilentlyContinue; return }
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut($startupLink)
    $link.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Background"
    $link.WorkingDirectory = $ninjaRoot
    $link.IconLocation = (Join-Path $ninjaRoot 'assets\ninja.ico')
    $link.WindowStyle = 7
    $link.Save()
}

# One tray per user: a second launch signals the first to open or focus its window, then exits.
$mutex = New-Object System.Threading.Mutex($false, 'Local\NinjaAssistantTray')
$signal = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, 'Local\NinjaAssistantOpen')
if (-not $mutex.WaitOne(0)) { if (-not $Background) { [void]$signal.Set() }; exit 0 }

if ($Background) { [void](Start-Ninja) } else { Open-Ninja }

$text = [System.Drawing.Color]::FromArgb(244, 244, 245); $muted = [System.Drawing.Color]::FromArgb(161, 161, 170)
$ok = [System.Drawing.Color]::FromArgb(74, 222, 128); $bad = [System.Drawing.Color]::FromArgb(248, 113, 113)
$font = New-Object System.Drawing.Font('Segoe UI', 9)
$menu = New-Object System.Windows.Forms.ContextMenuStrip
$menu.Renderer = New-Object NinjaRenderer
$menu.Font = $font
$menu.Padding = New-Object System.Windows.Forms.Padding(2, 3, 2, 3)
function Add-Item($label, $action, $color = $text) {
    $item = New-Object System.Windows.Forms.ToolStripMenuItem($label)
    $item.ForeColor = $color
    $item.Padding = New-Object System.Windows.Forms.Padding(2, 1, 8, 1)
    if ($action) { $item.add_Click($action) }
    [void]$menu.Items.Add($item)
    return $item
}
function Add-Line { $line = New-Object System.Windows.Forms.ToolStripSeparator; [void]$menu.Items.Add($line) }

$statusItem = Add-Item 'Ninja Assistant' $null
$statusItem.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 9)
$serverItem = Add-Item 'Checking…' $null $muted
$gpuItem = Add-Item '' $null $muted
foreach ($i in $statusItem, $serverItem, $gpuItem) { $i.Enabled = $false }
Add-Line
$openItem = Add-Item 'Open Ninja' { Open-Ninja }
$openItem.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 9)
Add-Line
$unloadItem = Add-Item 'Free GPU memory' {
    try { [void](Invoke-Ninja '/assistant/models/unload' 'POST' @{ model = $script:loaded }); $tray.ShowBalloonTip(2500, 'GPU memory freed', "$script:loaded is unloaded. The next chat loads it again.", [System.Windows.Forms.ToolTipIcon]::None) }
    catch { $tray.ShowBalloonTip(3000, 'Could not free GPU memory', 'The model is busy with a reply or a media job; try again when it finishes.', [System.Windows.Forms.ToolTipIcon]::None) }
}
$restartItem = Add-Item 'Restart server' { Stop-Ninja; Start-Sleep -Milliseconds 800; if (Start-Ninja) { $tray.ShowBalloonTip(2000, 'Ninja restarted', 'The server and workers are running again.', [System.Windows.Forms.ToolTipIcon]::None) } }
Add-Line
$startupItem = Add-Item 'Start with Windows' { Set-Startup (-not $startupItem.Checked) }
Add-Item 'Open data folder' { Start-Process explorer.exe (Join-Path $ninjaRoot 'data') } | Out-Null
Add-Line
Add-Item 'Quit Ninja' {
    Stop-Ninja
    $tray.Visible = $false
    [System.Windows.Forms.Application]::Exit()
} | Out-Null

# Refreshed each time the menu opens, so the status rows are current without polling in the background.
$menu.add_Opening({
    $script:loaded = $null
    $running = Test-Ninja
    $serverItem.Text = if ($running) { '●  Running' + $(if ($script:server) { '' } else { ' · started elsewhere' }) } else { '●  Stopped' }
    $serverItem.ForeColor = if ($running) { $ok } else { $bad }
    $gpuItem.Visible = $false
    if ($running) {
        try {
            $models = Invoke-Ninja '/assistant/models'
            $serverItem.Text += ' · ' + ($models.model -split '/')[-1]
            $memory = $models.memory.PSObject.Properties | Where-Object { $_.Value.vram } | Select-Object -First 1
            if ($memory) { $script:loaded = $memory.Name; $unloadText = 'Free GPU memory  (' + [math]::Round($memory.Value.vram / 1GB, 1) + ' GB)' }
            $gpu = Invoke-Ninja '/assistant/gpu'
            if ($gpu.gpu) {
                $gpuItem.Text = "GPU $($gpu.gpu.temperature)°C  ·  $($gpu.gpu.load)%  ·  " + [math]::Round($gpu.gpu.memory_used / 1GB, 1) + '/' + [math]::Round($gpu.gpu.memory_total / 1GB, 1) + ' GB' + $(if ($gpu.tokens_per_second) { '  ·  ' + [math]::Round($gpu.tokens_per_second) + ' tok/s' } else { '' })
                $gpuItem.Visible = $true
            }
        } catch {}  # Status rows only; the menu still works.
    }
    $unloadItem.Text = if ($script:loaded) { $unloadText } else { 'Free GPU memory  (nothing loaded)' }
    $unloadItem.Enabled = [bool]$script:loaded
    $restartItem.Visible = [bool]$script:server
    $startupItem.Checked = Test-Path $startupLink
})

$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Icon = New-Object System.Drawing.Icon (Join-Path $ninjaRoot 'assets\ninja.ico')
$tray.Text = 'Ninja Assistant'
$tray.ContextMenuStrip = $menu
$tray.add_MouseClick({ param($s, $e) if ($e.Button -eq [System.Windows.Forms.MouseButtons]::Left) { Open-Ninja } })
$tray.Visible = $true
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 300
$timer.add_Tick({ if ($signal.WaitOne(0)) { Open-Ninja } })
$timer.Start()
if (-not $Background) { $tray.ShowBalloonTip(3000, 'Ninja is running', 'Closing the window keeps Ninja in the background. Right-click this icon for more.', [System.Windows.Forms.ToolTipIcon]::None) }
try { [System.Windows.Forms.Application]::Run() } finally { Stop-Ninja; $tray.Dispose(); $mutex.ReleaseMutex() }
