# Install Microsoft TRELLIS on Windows (Anaconda + CUDA).
# Run in "Anaconda PowerShell Prompt". Needs NVIDIA GPU (~16 GB+ VRAM).
# Based on working Windows setups from microsoft/TRELLIS#3.
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dest = Join-Path $Root "third_party\repos\TRELLIS"

Write-Host "Pipeline root: $Root"
Write-Host "TRELLIS dest:  $Dest"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
  Write-Error "conda not found. Open Anaconda PowerShell Prompt, or install Miniconda."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Error "git not found."
}

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  nvidia-smi | Select-Object -First 12
} else {
  Write-Warning "nvidia-smi missing — GPU driver may not be on PATH."
}

New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
if (-not (Test-Path (Join-Path $Dest ".git"))) {
  git clone --recurse-submodules https://github.com/microsoft/TRELLIS.git $Dest
} else {
  Push-Location $Dest
  git submodule update --init --recursive
  Pop-Location
}

conda create -n trellis python=3.10 -y
conda run -n trellis conda install pytorch==2.5.0 torchvision==0.20.0 pytorch-cuda=12.4 -c pytorch -c nvidia -y

$env:SPCONV_ALGO = "native"
conda run -n trellis pip install --upgrade pip
conda run -n trellis pip install `
  imageio imageio-ffmpeg tqdm easydict opencv-python-headless `
  scipy ninja pybind11 pillow rembg onnxruntime onnxruntime-gpu `
  trimesh xatlas pyvista pymeshfix igraph utils3d flask

conda run -n trellis pip install xformers --index-url https://download.pytorch.org/whl/cu124
try {
  conda run -n trellis pip install flash-attn --no-build-isolation
} catch {
  Write-Warning "flash-attn failed (common on Windows). Use ATTN_BACKEND=xformers when serving."
}

conda run -n trellis pip install spconv-cu124
try {
  conda run -n trellis pip install git+https://github.com/NVlabs/nvdiffrast.git
} catch {
  Write-Warning "nvdiffrast skipped: $_"
}
try {
  conda run -n trellis pip install kaolin -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.0_cu124.html
} catch {
  Write-Warning "kaolin skipped: $_"
}

Write-Host ""
Write-Host "Done. Start the server from ai-3d-pipeline:"
Write-Host "  .\scripts\serve_trellis.ps1"
