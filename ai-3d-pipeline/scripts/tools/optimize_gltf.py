#!/usr/bin/env python3
"""Step LOD/export — run glTF-Transform optimize on a GLB (free)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--texture-size", type=int, default=1024)
    args = ap.parse_args()
    out = args.output or args.input.with_name(args.input.stem + "_opt.glb")

    cmd = [
        "npx",
        "--yes",
        "@gltf-transform/cli",
        "optimize",
        str(args.input),
        str(out),
        "--texture-size",
        str(args.texture_size),
    ]
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    sys.exit(main())
