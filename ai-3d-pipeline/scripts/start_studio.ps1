# Launch the local 3D Pipeline Studio (Windows).
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$env:BLENDER_BIN = if ($env:BLENDER_BIN) { $env:BLENDER_BIN } else { "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" }

Write-Host "Starting Studio at http://127.0.0.1:8787/"
Write-Host "Blender: $env:BLENDER_BIN"
python (Join-Path $Root "studio\server.py")
