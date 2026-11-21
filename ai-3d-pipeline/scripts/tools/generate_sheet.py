#!/usr/bin/env python3
"""
Step 02 / 06 — generate orthographic / turnaround sheets for free via HF FLUX.

Uses black-forest-labs/FLUX.1-schnell (ZeroGPU). Optional HF_TOKEN raises quota.
If a concept image exists, we still T2I with a strong match-the-design prompt
(FLUX.schnell Space is text-only); concept is kept as reference alongside.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from PIL import Image


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")


def _flux_t2i(prompt: str, out: Path, *, width: int = 1280, height: int = 576) -> Path:
    from gradio_client import Client

    token = _hf_token()
    client = Client("black-forest-labs/FLUX.1-schnell", token=token)
    result = client.predict(
        prompt=prompt,
        seed=0,
        randomize_seed=True,
        width=int(width),
        height=int(height),
        num_inference_steps=4,
        api_name="/infer",
    )
    src = result[0] if isinstance(result, (list, tuple)) else result
    if not src or not Path(src).exists():
        raise RuntimeError(f"FLUX returned no image: {result!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    # may be webp — normalize to png
    img = Image.open(src).convert("RGB")
    out = out.with_suffix(".png")
    img.save(out, format="PNG")
    return out


def _has_split_views(kind: str, out_dir: Path) -> bool:
    if kind == "character":
        return (out_dir / "view_front.png").exists() and (
            (out_dir / "view_right.png").exists() or (out_dir / "view_back.png").exists()
        )
    return (out_dir / "front.png").exists() and (out_dir / "side.png").exists()


def character_prompts(design: str) -> dict[str, str]:
    base = (
        f"{design}. Orthographic game-character turnaround, A-pose, arms away from body, "
        "legs slightly apart, empty hands (no weapons, no props in hands), flat even light, "
        "light grey background, no shadows, no perspective, full body visible, clean silhouette."
    )
    return {
        "view_front.png": f"{base} FRONT VIEW only, facing camera, single figure centered.",
        "view_right.png": f"{base} RIGHT SIDE VIEW only, profile facing right, single figure centered.",
        "view_back.png": f"{base} BACK VIEW only, facing away, single figure centered.",
    }


def prop_prompts(design: str) -> dict[str, str]:
    base = (
        f"{design}. Orthographic product / prop reference, flat colours, plain white background, "
        "no shadows, no reflections, no perspective, entire object visible, same scale."
    )
    return {
        "front.png": f"{base} FRONT VIEW only, single object centered.",
        "side.png": f"{base} SIDE VIEW only, exactly side-on, single object centered.",
        "top.png": f"{base} TOP VIEW only, looking straight down, single object centered.",
    }


def generate_views(
    *,
    kind: str,
    design: str,
    out_dir: Path,
    concept: Path | None = None,
    force: bool = False,
    mode: str = "panels",  # panels | sheet
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    if concept and concept.exists():
        # keep original concept for the user / split fallback
        dest = out_dir / ("concept.png" if kind == "character" else "concept.png")
        if concept.resolve() != dest.resolve():
            shutil.copy2(concept, dest)
        design = (
            f"{design}. Match this uploaded concept design closely (same silhouette, colours, details)."
            if design.strip()
            else "Match the uploaded concept design closely (same silhouette, colours, details)."
        )

    if _has_split_views(kind, out_dir) and not force:
        return {"skipped": True, "reason": "views already present", "out": str(out_dir)}

    saved: dict[str, str] = {}
    if mode == "sheet":
        sheet_prompt = (
            "Character turnaround sheet: front, right side, back in a horizontal row. "
            "Orthographic, same height, A-pose, empty hands, light grey background, flat light. "
            f"Design: {design}"
            if kind == "character"
            else "Orthographic reference sheet: front, side, top in a horizontal row. "
            "Plain white background, flat colours, no shadows. "
            f"Object: {design}"
        )
        sheet = _flux_t2i(sheet_prompt, out_dir / "sheet_gen.png", width=1536, height=512)
        saved["sheet"] = str(sheet)
        sys_path = Path(__file__).resolve().parent
        import sys

        sys.path.insert(0, str(sys_path))
        from split_sheet import save_character_views, save_prop_views

        split = (
            save_character_views(sheet, out_dir)
            if kind == "character"
            else save_prop_views(sheet, out_dir)
        )
        saved.update(split)
        return {"mode": "sheet", "saved": saved, "backend": "flux_schnell"}

    prompts = character_prompts(design) if kind == "character" else prop_prompts(design)
    # slightly square panels for cleaner silhouettes
    for name, prompt in prompts.items():
        path = _flux_t2i(prompt, out_dir / name, width=768, height=1024 if kind == "character" else 768)
        saved[name] = str(path)
    return {"mode": "panels", "saved": saved, "backend": "flux_schnell"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate turnaround / ortho sheets via free HF FLUX")
    ap.add_argument("--kind", choices=("character", "prop"), required=True)
    ap.add_argument("--prompt", default="", help="Design description")
    ap.add_argument("--concept", type=Path, default=None)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--mode", choices=("panels", "sheet"), default="panels")
    args = ap.parse_args()
    if not args.prompt.strip() and not (args.concept and args.concept.exists()):
        raise SystemExit("Need --prompt and/or --concept")
    info = generate_views(
        kind=args.kind,
        design=args.prompt.strip() or "game asset",
        out_dir=args.out,
        concept=args.concept,
        force=args.force,
        mode=args.mode,
    )
    print(info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
