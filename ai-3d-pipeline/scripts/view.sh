#!/usr/bin/env bash
# Serve the pipeline folder and open the Three.js FBX/GLB viewer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8765}"
SRC="${1:-examples/props/crate/exports/crate.glb}"
cd "$ROOT"
python3 -m http.server "$PORT" --bind 127.0.0.1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
URL="http://127.0.0.1:${PORT}/viewer/?src=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "../$SRC")"
echo "Viewer: $URL"
echo "Serving $ROOT on :$PORT (Ctrl+C to stop)"
if command -v xdg-open >/dev/null; then xdg-open "$URL" || true; fi
wait "$PID"
