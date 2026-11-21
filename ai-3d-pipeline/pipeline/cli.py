#!/usr/bin/env python3
"""Orchestrate the free AI 3D pipeline (props + characters)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .blender_runner import run_blender_script
from .config import ROOT, ensure_asset_dirs, load_config


def run_step(script_rel: str, args: dict) -> None:
    script = ROOT / script_rel
    if not script.exists():
        raise FileNotFoundError(script)
    run_blender_script(script, args=args)


def cmd_measure(name: str, *, width: float, depth: float, height: float) -> None:
    """Step 02–03: split concept sheet if needed, measure refs → parts.json."""
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    from measure_parts import measure  # type: ignore
    from split_sheet import save_prop_views  # type: ignore

    base = ensure_asset_dirs("props", name)
    refs = base / "references"
    concept = refs / "concept.png"
    if concept.exists() and not (refs / "side.png").exists():
        print("=== split concept sheet → front/side/top ===")
        save_prop_views(concept, refs)
    front, side = refs / "front.png", refs / "side.png"
    if not side.exists() and not front.exists():
        raise SystemExit(f"Need {refs}/front.png or side.png (or concept.png to split)")
    doc = measure(
        front=front if front.exists() else None,
        side=side if side.exists() else None,
        name=name,
        width_m=width,
        depth_m=depth,
        height_m=height,
    )
    out = base / "parts.json"
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(doc['parts'])} parts, contour on tallest)")


def cmd_prop(name: str, *, remeasure: bool = False) -> None:
    """Steps 03–05 for a code-built prop (demo: crate)."""
    base = ensure_asset_dirs("props", name)
    parts = base / "parts.json"
    if remeasure or not parts.exists():
        cmd_measure(name, width=0.6, depth=0.6, height=0.5)
    if not parts.exists():
        raise SystemExit(f"Missing {parts} — write measurements first (step 03).")

    doc = json.loads(parts.read_text())
    for part in doc["parts"]:
        print(f"\n=== build part {part['name']} ({part.get('build', 'box')}) ===")
        run_step("blender/props/build_part.py", {"asset": name, "part": part["name"], "render_px": 768})

    print("\n=== assemble + export ===")
    run_step("blender/props/assemble.py", {"asset": name})

    glb = base / "exports" / f"{name}.glb"
    if glb.exists():
        opt = base / "exports" / f"{name}_opt.glb"
        subprocess.call(
            [sys.executable, str(ROOT / "scripts/tools/optimize_gltf.py"), str(glb), "-o", str(opt)],
            cwd=str(ROOT),
        )
    print(f"\nDone. Exports in {base / 'exports'}")


def cmd_buildings(count: int = 10) -> None:
    ensure_asset_dirs("props", "buildings")
    run_step("blender/props/buildings.py", {"count": count})


def cmd_generate(name: str, *, force: bool = False) -> None:
    """Step 06–07: split turnaround sheet + Hunyuan→TRELLIS→HF TripoSR chain."""
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    sys.path.insert(0, str(ROOT / "scripts" / "characters"))
    from split_sheet import save_character_views  # type: ignore
    import importlib

    chain = importlib.import_module("07_generate_chain")

    base = ensure_asset_dirs("characters", name)
    views = base / "views"
    concept = views / "view_front.png"
    for cand in (views / "concept.png", base / "references" / "concept.png"):
        if cand.exists():
            concept = cand
            break
    if concept.exists() and not (views / "view_right.png").exists():
        print("=== split turnaround → front/right/back ===")
        save_character_views(concept, views)
    out = base / "exports" / "raw.glb"
    if out.exists() and not force:
        print(f"raw.glb already exists ({out}); pass --force to regenerate")
        return
    backend = chain.generate(base, out)
    print(f"backend={backend} → {out}")


def cmd_character(name: str, *, from_glb: Path | None = None, demo: bool = False, generate: bool = False) -> None:
    """
    Free character path:
      generate OR demo mesh OR import GLB → clean → split → joints → rig → pose test → clips → QC → export
    """
    base = ensure_asset_dirs("characters", name)
    raw = base / "exports" / "raw.glb"

    if generate:
        cmd_generate(name, force=True)
    elif from_glb:
        raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(from_glb, raw)
        print(f"imported {from_glb}")
    elif demo or (not raw.exists() and from_glb is None):
        print("=== make free demo mesh (no API) ===")
        run_step("blender/characters/make_demo_mesh.py", {"asset": name})

    if not raw.exists():
        raise SystemExit(
            "No raw.glb. Drop a generator GLB at "
            f"{raw} or pass --glb / --demo / --generate"
        )

    cfg = load_config()["characters"]
    steps = [
        ("blender/characters/clean.py", {"asset": name, "input": str(raw), **{k: cfg[k] for k in ("height_m", "hero_triangles", "crowd_triangles")}}),
        ("blender/characters/split_parts.py", {"asset": name}),
        ("blender/characters/joints.py", {"asset": name}),
        ("blender/characters/rig_weights.py", {"asset": name}),
        ("blender/characters/pose_test.py", {"asset": name}),
        ("blender/characters/clips/idle.py", {"asset": name}),
        ("blender/characters/clips/walk.py", {"asset": name}),
        ("blender/characters/check_clips.py", {"asset": name}),
        ("blender/characters/export_fbx.py", {"asset": name}),
    ]
    for script, args in steps:
        print(f"\n=== {script} ===")
        run_step(script, args)

    glb = base / "exports" / f"{name}.glb"
    if glb.exists():
        subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts/tools/optimize_gltf.py"),
                str(glb),
                "-o",
                str(base / "exports" / f"{name}_opt.glb"),
            ],
            cwd=str(ROOT),
        )
    print(f"\nDone. Character exports in {base / 'exports'}")


def cmd_doctor() -> None:
    cfg = load_config()
    blender = cfg.get("blender_bin", "blender")
    print("ROOT", ROOT)
    print("blender_bin", blender)
    try:
        out = subprocess.check_output([blender, "--version"], text=True)
        print(out.splitlines()[0])
    except Exception as e:
        print("Blender NOT found:", e)
    for pkg in ("yaml", "PIL", "numpy", "requests", "cv2", "gradio_client"):
        mod = {"PIL": "PIL", "yaml": "yaml", "cv2": "cv2"}.get(pkg, pkg)
        try:
            __import__(mod if pkg != "PIL" else "PIL")
            print(f"py:{pkg} OK")
        except ImportError:
            print(f"py:{pkg} MISSING")
    print("gltf-transform:", shutil.which("npx"))
    gen = cfg.get("characters", {}).get("generator", "import")
    print(f"Configured generator: {gen} (chain: hunyuan → trellis → HF TripoSR)")
    trellis = ROOT / "third_party" / "repos" / "TRELLIS"
    print("TRELLIS clone:", "OK" if trellis.is_dir() else "not installed (needs NVIDIA CUDA)")
    hun = ROOT / "third_party" / "Hunyuan3D-2-WinPortable"
    print("Hunyuan portable dir:", "OK" if hun.is_dir() else "run scripts/install_hunyuan_portable.ps1")
    import os
    import urllib.request

    for label, url in (("Hunyuan :8080", os.environ.get("HUNYUAN_URL", "http://127.0.0.1:8080")),
                       ("TRELLIS :8090", os.environ.get("TRELLIS_URL", "http://127.0.0.1:8090"))):
        try:
            urllib.request.urlopen(url, timeout=1)
            print(f"{label}: UP")
        except Exception:
            print(f"{label}: down (HF TripoSR fallback)")
    print("Studio app: python studio/server.py  →  http://127.0.0.1:8787/")
    print("All generators are local/$0 — Tripo API remains optional paid only.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Free AI 3D modeling pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prop = sub.add_parser("prop", help="Build a measured prop (steps 03–05)")
    p_prop.add_argument("name", help="Asset folder under examples/props/")
    p_prop.add_argument("--remeasure", action="store_true", help="Re-run OpenCV measure from refs")

    p_m = sub.add_parser("measure", help="Split sheet + measure refs → parts.json (02–03)")
    p_m.add_argument("name")
    p_m.add_argument("--width", type=float, default=0.6)
    p_m.add_argument("--depth", type=float, default=0.6)
    p_m.add_argument("--height", type=float, default=0.5)

    p_b = sub.add_parser("buildings", help="Procedural buildings")
    p_b.add_argument("--count", type=int, default=10)

    p_c = sub.add_parser("character", help="Character cleanup→rig→clips→export")
    p_c.add_argument("name")
    p_c.add_argument("--glb", type=Path, default=None, help="Import generator GLB as raw.glb")
    p_c.add_argument("--demo", action="store_true", help="Use built-in free A-pose placeholder")
    p_c.add_argument("--generate", action="store_true", help="Run Hunyuan→TRELLIS→TripoSR chain first")

    p_g = sub.add_parser("generate", help="Split turnaround + generator chain → raw.glb (06–07)")
    p_g.add_argument("name")
    p_g.add_argument("--force", action="store_true")

    sub.add_parser("doctor", help="Check Blender + deps")

    args = parser.parse_args(argv)
    if args.cmd == "prop":
        cmd_prop(args.name, remeasure=args.remeasure)
    elif args.cmd == "measure":
        cmd_measure(args.name, width=args.width, depth=args.depth, height=args.height)
    elif args.cmd == "buildings":
        cmd_buildings(args.count)
    elif args.cmd == "character":
        cmd_character(
            args.name,
            from_glb=args.glb,
            demo=args.demo or (args.name == "demo" and not args.generate and not args.glb),
            generate=args.generate,
        )
    elif args.cmd == "generate":
        cmd_generate(args.name, force=args.force)
    elif args.cmd == "doctor":
        cmd_doctor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
