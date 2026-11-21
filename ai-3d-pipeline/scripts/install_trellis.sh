#!/usr/bin/env bash
# Linux TRELLIS install. On Windows use:  .\scripts\install_trellis.ps1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/third_party/repos/TRELLIS"

if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == CYGWIN* || -n "${WINDIR:-}" ]]; then
  echo "On Windows use PowerShell:  .\\scripts\\install_trellis.ps1"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: no NVIDIA GPU / nvidia-smi. TRELLIS needs ~16 GB+ VRAM."
  exit 1
fi
if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found (Miniconda/Anaconda)."
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
if [[ ! -d "$DEST/.git" ]]; then
  git clone --recurse-submodules https://github.com/microsoft/TRELLIS.git "$DEST"
else
  git -C "$DEST" submodule update --init --recursive
fi

cd "$DEST"
# shellcheck disable=SC1091
. ./setup.sh --new-env --basic --xformers --flash-attn --diffoctreerast --spconv --mipgaussian --kaolin --nvdiffrast
conda run -n trellis pip install -q flask trimesh pillow

echo "Done. Start: ./scripts/serve_trellis.sh"
