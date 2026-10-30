$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force data | Out-Null
Add-Type -AssemblyName System.Speech
$ninjaVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$ninjaVoice.SetOutputToWaveFile((Join-Path (Get-Location) 'data/sample.wav'))
$ninjaVoice.Speak('Welcome to Ninja Assistant. This is a real local video editing test. We preserve the original recording, review the captions, and render a short video. You stay in control of every action.')
$ninjaVoice.Dispose()
