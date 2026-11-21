#!/usr/bin/env python3
"""Optional PyMeshLab cleanup (step 08 assist / retopo prep)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--target-faces", type=int, default=20000)
    args = ap.parse_args()

    try:
        import pymeshlab
    except ImportError:
        print("Install optional dep: pip install pymeshlab", file=sys.stderr)
        return 1

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(args.input))
    ms.meshing_merge_close_vertices(threshold=pymeshlab.PureValue(0.0001))
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum=args.target_faces)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ms.save_current_mesh(str(args.output))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
