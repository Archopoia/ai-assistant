#!/usr/bin/env bash
# Linux TRELLIS server. On Windows use:  .\scripts\serve_trellis.ps1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TRELLIS_ROOT="${TRELLIS_ROOT:-$ROOT/third_party/repos/TRELLIS}"

if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == CYGWIN* || -n "${WINDIR:-}" ]]; then
  echo "On Windows use PowerShell:  .\\scripts\\serve_trellis.ps1"
  exit 1
fi
[[ -d "$TRELLIS_ROOT" ]] || { echo "Run ./scripts/install_trellis.sh first"; exit 1; }
command -v conda >/dev/null || { echo "conda not found"; exit 1; }

echo "Serving TRELLIS at http://127.0.0.1:8090"
exec conda run --no-capture-output -n trellis python "$ROOT/scripts/serve_trellis.py"
