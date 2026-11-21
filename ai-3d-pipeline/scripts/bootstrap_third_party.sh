#!/usr/bin/env bash
# Clone the free upstream tools from the article (optional; pipeline runs without them).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/third_party/repos"
mkdir -p "$DEST"
cd "$DEST"

clone() {
  local url="$1" name="$2"
  if [[ -d "$name/.git" ]]; then
    echo "exists $name"
  else
    git clone --depth 1 "$url" "$name"
  fi
}

# Claude × Blender
clone https://github.com/ahujasid/blender-mcp.git blender-mcp
clone https://github.com/EL4CTEO/blender-skills.git blender-skills

# Modeling
clone https://github.com/gumyr/build123d.git build123d
clone https://github.com/ranjian0/building_tools.git building_tools
# Tripo add-on/SDK are optional paid — skip by default

# Retopo & cleanup
clone https://github.com/huxingyi/autoremesher.git autoremesher
clone https://github.com/CGCookie/retopoflow.git retopoflow
clone https://github.com/cnr-isti-vclab/PyMeshLab.git PyMeshLab

# UVs & textures
clone https://github.com/jpcy/xatlas.git xatlas
clone https://github.com/RodZill4/material-maker.git material-maker
clone https://github.com/armory3d/armorpaint.git armorpaint

# LODs & export
clone https://github.com/zeux/meshoptimizer.git meshoptimizer
clone https://github.com/donmccurdy/glTF-Transform.git glTF-Transform

# Free EU-safe character generators
clone https://github.com/VAST-AI-Research/TripoSR.git TripoSR
clone https://github.com/microsoft/TRELLIS.git TRELLIS

echo "Done. Repos in $DEST"
echo "NOTE: Hunyuan3D intentionally omitted (licence excludes EU/UK/KR)."
