#!/usr/bin/env python3
"""
Step 07 — free character mesh generation chain.

Order:
  1. Local Hunyuan (HUNYUAN_URL / WinPortable :8080) multiview
  2. Local TRELLIS (TRELLIS_URL) multiview
  3. Hugging Face TripoSR (single best view) — works without NVIDIA
  4. Import existing GLB
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]


def _post_multiview(url: str, front: Path, right: Path | None, back: Path | None, out: Path) -> None:
    opened = []
    try:
        files = {"front": ("view_front.png", front.open("rb"), "image/png")}
        opened.append(files["front"][1])
        if right and right.exists():
            files["right"] = ("view_right.png", right.open("rb"), "image/png")
            opened.append(files["right"][1])
        if back and back.exists():
            files["back"] = ("view_back.png", back.open("rb"), "image/png")
            opened.append(files["back"][1])
        r = requests.post(f"{url.rstrip('/')}/multiview", files=files, timeout=900)
        if r.status_code >= 400:
            for f in opened:
                f.close()
            opened.clear()
            with front.open("rb") as fh:
                r = requests.post(
                    f"{url.rstrip('/')}/generate",
                    files={"image": ("view_front.png", fh, "image/png")},
                    timeout=900,
                )
        r.raise_for_status()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        print(f"saved {out} via {url}")
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


def _triposr_hf(front: Path, out: Path) -> None:
    from gradio_client import Client, handle_file

    print("HF TripoSR…")
    client = Client("stabilityai/TripoSR")
    result = client.predict(handle_file(str(front)), True, 0.85, 256, api_name="/generate")
    glb_src = None
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, str) and item.lower().endswith(".glb"):
                glb_src = item
                break
    elif isinstance(result, str) and result.lower().endswith(".glb"):
        glb_src = result
    if not glb_src or not Path(glb_src).exists():
        raise RuntimeError(f"TripoSR returned no GLB: {result!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(glb_src, out)
    print(f"saved {out} via HF TripoSR")


def generate(asset_dir: Path, out: Path) -> str:
    views = asset_dir / "views"
    front = views / "view_front.png"
    right = views / "view_right.png"
    back = views / "view_back.png"
    if not front.exists():
        pngs = sorted(views.glob("*.png"))
        if not pngs:
            raise FileNotFoundError(f"No views in {views}")
        front = pngs[0]

    hunyuan = os.environ.get("HUNYUAN_URL", "http://127.0.0.1:8080")
    trellis = os.environ.get("TRELLIS_URL", "http://127.0.0.1:8090")

    for label, url in (("hunyuan", hunyuan), ("trellis", trellis)):
        try:
            requests.get(url, timeout=2)
        except Exception:
            continue
        try:
            _post_multiview(url, front, right if right.exists() else None, back if back.exists() else None, out)
            return label
        except Exception as e:
            print(f"{label} failed: {e}", file=sys.stderr)

    _triposr_hf(front, out)
    return "triposr_hf"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", type=Path, required=True, help="examples/characters/<name>")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--glb", type=Path, help="Skip generate; copy this GLB")
    args = ap.parse_args()
    out = args.output or (args.asset / "exports" / "raw.glb")
    if args.glb:
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.glb, out)
        print(f"imported {args.glb}")
        return 0
    backend = generate(args.asset, out)
    print(f"backend={backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
