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


def cmd_prop(name: str) -> None:
    """Steps 03–05 for a code-built prop (demo: crate)."""
    base = ensure_asset_dirs("props", name)
    parts = base / "parts.json"
    if not parts.exists():
        raise SystemExit(f"Missing {parts} — write measurements first (step 03).")

    doc = json.loads(parts.read_text())
    for part in doc["parts"]:
        print(f"\n=== build part {part['name']} ===")
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


def cmd_character(name: str, *, from_glb: Path | None = None, demo: bool = False) -> None:
    """
    Free character path:
      demo mesh OR import GLB → clean → split → joints → rig → pose test → clips → QC → export
    """
    base = ensure_asset_dirs("characters", name)
    raw = base / "exports" / "raw.glb"

    if demo or (not raw.exists() and from_glb is None):
        print("=== make free demo mesh (no API) ===")
        run_step("blender/characters/make_demo_mesh.py", {"asset": name})
    elif from_glb:
        raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(from_glb, raw)
        print(f"imported {from_glb}")

    if not raw.exists():
        raise SystemExit(
            "No raw.glb. Drop a generator GLB at "
            f"{raw} or pass --glb / --demo"
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
    for pkg in ("yaml", "PIL", "numpy", "requests"):
        try:
            __import__(pkg if pkg != "PIL" else "PIL")
            print(f"py:{pkg} OK")
        except ImportError:
            print(f"py:{pkg} MISSING")
    print("gltf-transform:", shutil.which("npx"))
    print(
        "Free character backends: import | triposr | trellis | hunyuan "
        "(default: trellis — Windows: .\\scripts\\install_trellis.ps1)"
    )
    trellis = ROOT / "third_party" / "repos" / "TRELLIS"
    print(
        "TRELLIS clone:",
        "OK" if trellis.is_dir() else "MISSING — run .\\scripts\\install_trellis.ps1 on your Windows GPU PC",
    )
    print("All generators are local/$0 — Tripo API remains optional paid only.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Free AI 3D modeling pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prop = sub.add_parser("prop", help="Build a measured prop (steps 03–05)")
    p_prop.add_argument("name", help="Asset folder under examples/props/")

    p_b = sub.add_parser("buildings", help="Procedural buildings")
    p_b.add_argument("--count", type=int, default=10)

    p_c = sub.add_parser("character", help="Character cleanup→rig→clips→export")
    p_c.add_argument("name")
    p_c.add_argument("--glb", type=Path, default=None, help="Import generator GLB as raw.glb")
    p_c.add_argument("--demo", action="store_true", help="Use built-in free A-pose placeholder")

    sub.add_parser("doctor", help="Check Blender + deps")

    args = parser.parse_args(argv)
    if args.cmd == "prop":
        cmd_prop(args.name)
    elif args.cmd == "buildings":
        cmd_buildings(args.count)
    elif args.cmd == "character":
        cmd_character(args.name, from_glb=args.glb, demo=args.demo or args.name == "demo")
    elif args.cmd == "doctor":
        cmd_doctor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
