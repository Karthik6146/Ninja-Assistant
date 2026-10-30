param([string]$TextFile,[string]$OutputFile,[string]$Voice,[switch]$List)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$ninjaSpeaker=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if($List){ConvertTo-Json -InputObject @($ninjaSpeaker.GetInstalledVoices() | Where-Object Enabled | ForEach-Object {$_.VoiceInfo.Name}) -Compress;return}
    if(-not $Voice){throw 'Choose an installed local narration voice.'}
    $ninjaSpeaker.SelectVoice($Voice)
    $ninjaSpeaker.SetOutputToWaveFile($OutputFile)
    $ninjaSpeaker.Speak([IO.File]::ReadAllText($TextFile))
} finally {$ninjaSpeaker.Dispose()}
