$ErrorActionPreference='Stop'
$ninjaRoot=Split-Path $PSScriptRoot -Parent
$ninjaService=Join-Path $ninjaRoot 'data/services/openchatcut'
if(-not(Test-Path -LiteralPath $ninjaService)){throw 'Run scripts/setup-video-services.ps1 first.'}
Push-Location $ninjaService
try {
    $env:OPENCHATCUT_DEV_PROFILE_ID='52e8c6d2-2d3d-4aae-9be7-fb2f4f40996c'
    # Only the media folders Ninja imports from; never data/ itself (token, credentials, databases).
    $env:AGENT_IMPORT_ROOTS=(Join-Path $ninjaRoot 'data/video-sources')+','+(Join-Path $ninjaRoot 'data/projects')
    & node (Join-Path $PSScriptRoot 'start-editor.mjs')
    if($LASTEXITCODE -ne 0){throw "Editor exited with code $LASTEXITCODE"}
} finally {Pop-Location}
