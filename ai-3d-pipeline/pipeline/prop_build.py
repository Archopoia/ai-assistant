"""Step 04–05 orchestrator: build each part with ≤3 render-vs-ref fix rounds, then assemble."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .blender_runner import run_blender_script
from .config import ROOT, ensure_asset_dirs, load_config


def _compare(render: Path, ref: Path, height_m: float, combo: Path) -> dict:
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    from compare_part import compare, save_combo  # type: ignore

    r = compare(render, ref, expected_height_m=height_m)
    save_combo(r, combo)
    return {k: v for k, v in r.items() if k != "combo_bgr"}


def build_parts_with_qc(name: str, *, log=print) -> dict:
    cfg = load_config().get("props", {})
    max_rounds = int(cfg.get("max_fix_rounds", 3))
    render_px = int(cfg.get("render_px", 768))
    base = ensure_asset_dirs("props", name)
    parts_path = base / "parts.json"
    doc = json.loads(parts_path.read_text(encoding="utf-8"))
    qc_all = {}

    for part in doc["parts"]:
        pname = part["name"]
        log(f"04 · Build part “{pname}” (≤{max_rounds} QC rounds)")
        last = None
        for round_i in range(1, max_rounds + 1):
            run_blender_script(
                ROOT / "blender/props/build_part.py",
                args={"asset": name, "part": pname, "render_px": render_px, "round": round_i},
            )
            side_render = base / "renders" / f"{pname}_side.png"
            side_ref = base / "references" / "side.png"
            if not side_ref.exists() or not side_render.exists():
                log(f"  round {round_i}: no side ref — skip QC")
                last = {"ok": True, "note": "no_ref"}
                break
            combo = base / "renders" / f"{pname}_side_vs_ref_r{round_i}.png"
            last = _compare(side_render, side_ref, float(part["height"]), combo)
            log(
                f"  round {round_i}: score={last.get('score')} "
                f"diff_cm={last.get('diff_cm')} ok={last.get('ok')}"
            )
            qc_all[f"{pname}_r{round_i}"] = last
            if last.get("ok"):
                break
            # guide: fix sizes from cm deltas / scale hints
            hint = last.get("scale_hint") or {}
            sh = float(hint.get("height", 1.0))
            sw = float(hint.get("width", 1.0))
            # clamp corrections
            sh = max(0.85, min(1.15, sh))
            sw = max(0.85, min(1.15, sw))
            part["height"] = round(float(part["height"]) * sh, 4)
            part["width"] = round(float(part["width"]) * sw, 4)
            part["depth"] = round(float(part.get("depth", part["width"])) * sw, 4)
            # rewrite this part in doc
            for i, p in enumerate(doc["parts"]):
                if p["name"] == pname:
                    doc["parts"][i] = part
                    break
            parts_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            log(f"  adjusted → h={part['height']} w={part['width']} d={part['depth']}")
        else:
            log(f"  max rounds reached for {pname}; continuing with best effort")
        qc_all[pname] = last

    (base / "parts" / "build_qc.json").write_text(json.dumps(qc_all, indent=2), encoding="utf-8")
    log("05 · Assemble + export")
    run_blender_script(ROOT / "blender/props/assemble.py", args={"asset": name})
    return {"name": name, "qc": qc_all, "exports": str(base / "exports")}
