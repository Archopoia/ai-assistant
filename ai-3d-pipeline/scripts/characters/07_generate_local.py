#!/usr/bin/env python3
"""
Free character generation client (EU-safe).

Points at a local TripoSR or TRELLIS HTTP server, or copies a provided GLB.
Hunyuan3D is intentionally unsupported (licence excludes EU/UK/KR).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import requests


def post_multiview(url: str, front: Path, right: Path | None, back: Path | None, out: Path) -> None:
    files = {"front": front.open("rb")}
    if right:
        files["right"] = right.open("rb")
    if back:
        files["back"] = back.open("rb")
    try:
        r = requests.post(f"{url.rstrip('/')}/multiview", files=files, timeout=600)
        r.raise_for_status()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        print(f"saved {out}")
    finally:
        for f in files.values():
            f.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Free local image→3D (TripoSR/TRELLIS) or import GLB")
    ap.add_argument("--backend", choices=("import", "triposr", "trellis"), default="import")
    ap.add_argument("--glb", type=Path, help="Existing GLB to import (backend=import)")
    ap.add_argument("--front", type=Path)
    ap.add_argument("--right", type=Path)
    ap.add_argument("--back", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    if args.backend == "import":
        if not args.glb or not args.glb.exists():
            print("Provide --glb for import backend", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(args.glb, args.output)
        print(f"imported {args.glb} → {args.output}")
        return 0

    if not args.front:
        print("--front required for generator backends", file=sys.stderr)
        return 2

    url = os.environ.get(
        "TRIPOSR_URL" if args.backend == "triposr" else "TRELLIS_URL",
        "http://127.0.0.1:7860" if args.backend == "triposr" else "http://127.0.0.1:8090",
    )
    try:
        post_multiview(url, args.front, args.right, args.back, args.output)
    except requests.RequestException as e:
        print(
            f"Local {args.backend} server not reachable at {url}: {e}\n"
            "Start TripoSR or TRELLIS locally, or use --backend import --glb path.glb\n"
            "See third_party/SOURCES.md",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
