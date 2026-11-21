#!/usr/bin/env python3
"""Optional xatlas UV unwrap for a mesh exported as OBJ."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="OBJ input")
    ap.add_argument("-o", "--output", type=Path, required=True, help="OBJ output with UVs")
    args = ap.parse_args()

    try:
        import xatlas
        import numpy as np
    except ImportError:
        print("Install optional dep: pip install xatlas", file=sys.stderr)
        return 1

    # minimal OBJ loader
    verts = []
    faces = []
    for line in args.input.read_text().splitlines():
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            idx = []
            for part in line.split()[1:]:
                idx.append(int(part.split("/")[0]) - 1)
            if len(idx) >= 3:
                for i in range(1, len(idx) - 1):
                    faces.append([idx[0], idx[i], idx[i + 1]])
    vmapping, indices, uvs = xatlas.parametrize(np.array(verts, dtype=np.float32), np.array(faces, dtype=np.uint32))
    out_v = np.array(verts, dtype=np.float32)[vmapping]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        for v in out_v:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for uv in uvs:
            f.write(f"vt {uv[0]} {uv[1]}\n")
        for i in range(0, len(indices), 3):
            a, b, c = indices[i : i + 3] + 1
            f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
