# Wire Hunyuan3D-2 WinPortable (free local generator, NVIDIA).
# Downloads are large (~3GB). Requires NVIDIA GPU.
# https://github.com/YanWenKun/Hunyuan3D-2-WinPortable
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dest = Join-Path $Root "third_party\Hunyuan3D-2-WinPortable"
$Marker = Join-Path $Dest "README_PIPELINE.txt"

Write-Host "Hunyuan WinPortable target: $Dest"
Write-Host "Official pack: https://github.com/YanWenKun/Hunyuan3D-2-WinPortable"

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
  $gpu = (Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ", "
  Write-Warning "No nvidia-smi. Detected: $gpu"
  Write-Warning "Hunyuan needs NVIDIA. Scripts are still wired; Studio will fall back to HF TripoSR."
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

@"
Hunyuan3D-2 WinPortable — pipeline notes
========================================

1. Download the split 7z for your CUDA (cu129 or cu126) from:
   https://github.com/YanWenKun/Hunyuan3D-2-WinPortable/releases

2. Extract BOTH .001/.002 parts into:
   $Dest

3. Run the pack's launcher / RUN.bat (multiview server on http://127.0.0.1:8080).

4. In this pipeline:
   `$env:HUNYUAN_URL = "http://127.0.0.1:8080"`
   Then character generate uses Hunyuan first (see scripts/characters/07_generate_chain.py).

Studio / CLI will auto-detect a live server on :8080.
"@ | Set-Content -Path $Marker -Encoding UTF8

# Clone helper README repo (tiny) for docs link — optional
$Docs = Join-Path $Root "third_party\repos"
New-Item -ItemType Directory -Force -Path $Docs | Out-Null
if (-not (Test-Path (Join-Path $Docs "Hunyuan3D-2-WinPortable\.git"))) {
  try {
    git clone --depth 1 https://github.com/YanWenKun/Hunyuan3D-2-WinPortable.git (Join-Path $Docs "Hunyuan3D-2-WinPortable")
  } catch {
    Write-Warning "Could not clone docs repo: $_"
  }
}

Write-Host ""
Write-Host "Wrote $Marker"
Write-Host "After extracting the portable pack and starting it, set HUNYUAN_URL and generate."
Write-Host "Start Studio: .\\scripts\\start_studio.ps1"
