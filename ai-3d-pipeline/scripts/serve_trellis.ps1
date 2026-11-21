# Start local TRELLIS /multiview server on Windows (http://127.0.0.1:8090).
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dest = Join-Path $Root "third_party\repos\TRELLIS"
$Server = Join-Path $Root "scripts\serve_trellis.py"

if (-not (Test-Path $Dest)) {
  Write-Error "TRELLIS not found at $Dest. Run .\scripts\install_trellis.ps1 first."
}
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
  Write-Error "conda not found. Open Anaconda PowerShell Prompt."
}

$env:TRELLIS_ROOT = $Dest
$env:SPCONV_ALGO = "native"
if (-not $env:ATTN_BACKEND) { $env:ATTN_BACKEND = "xformers" }
if (-not $env:TRELLIS_MODEL) { $env:TRELLIS_MODEL = "microsoft/TRELLIS-image-large" }

Write-Host "Serving TRELLIS at http://127.0.0.1:8090 (model=$($env:TRELLIS_MODEL))"
Write-Host "ATTN_BACKEND=$($env:ATTN_BACKEND)"
conda run --no-capture-output -n trellis python $Server
