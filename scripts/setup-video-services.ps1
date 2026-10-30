$ErrorActionPreference='Stop'
$ninjaRoot=Split-Path $PSScriptRoot -Parent
function Checked([string]$Command,[string[]]$Arguments){& $Command @Arguments;if($LASTEXITCODE -ne 0){throw "$Command failed with code $LASTEXITCODE"}}
function Repository([string]$Url,[string]$Path,[string]$Revision){
    if(-not(Test-Path -LiteralPath $Path)){
        Checked 'git' @('clone','--no-checkout',$Url,$Path)
        Checked 'git' @('-C',$Path,'checkout','--detach',$Revision)
    }
    $ninjaRevision=& git -C $Path rev-parse HEAD
    if($ninjaRevision -ne $Revision){throw "Existing service revision differs at $Path. Preserve/review its changes before updating."}
}
$ninjaServices=Join-Path $ninjaRoot 'data/services'
New-Item -ItemType Directory -Force $ninjaServices | Out-Null
Repository 'https://github.com/0xsline/OpenChatCut.git' (Join-Path $ninjaServices 'openchatcut') '297b3279e8f34bd8cb984a64634efdd8db3cb858'
Push-Location (Join-Path $ninjaServices 'openchatcut')
try {Checked 'npm.cmd' @('ci','--ignore-scripts','--no-audit','--no-fund')} finally {Pop-Location}
Write-Host 'Services installed separately. Start the editor with scripts/start-video-service.ps1.'
