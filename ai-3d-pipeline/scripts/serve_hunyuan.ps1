# Start Hunyuan3D-2 WinPortable if extracted, else print setup steps.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dest = Join-Path $Root "third_party\Hunyuan3D-2-WinPortable"

$env:HUNYUAN_URL = if ($env:HUNYUAN_URL) { $env:HUNYUAN_URL } else { "http://127.0.0.1:8080" }

$launchers = @(
  (Join-Path $Dest "RUN.bat"),
  (Join-Path $Dest "run.bat"),
  (Join-Path $Dest "start.bat"),
  (Join-Path $Dest "app.py")
) | Where-Object { Test-Path $_ }

if (-not $launchers) {
  Write-Host "Hunyuan portable not extracted at $Dest"
  Write-Host "Run: .\scripts\install_hunyuan_portable.ps1"
  Write-Host "Then download the CUDA pack from:"
  Write-Host "  https://github.com/YanWenKun/Hunyuan3D-2-WinPortable/releases"
  Write-Host "Without NVIDIA, Studio falls back to HF TripoSR automatically."
  exit 1
}

$first = $launchers[0]
Write-Host "Starting Hunyuan from $first"
Write-Host "Expect multiview API at $env:HUNYUAN_URL"
if ($first -like "*.bat") {
  Start-Process -FilePath $first -WorkingDirectory $Dest
} else {
  Set-Location $Dest
  python $first
}
