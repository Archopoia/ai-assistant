#!/usr/bin/env python3
"""
Local Studio — tutorial funnel on 127.0.0.1:

  prompt and/or picture → pick route → one export pipeline

Routes (article step 01):
  prop       — orthographic refs → parts.json → Blender code (02–05)
  character  — turnaround sheet → TripoSR/Hunyuan/import → clean→rig→clips (06–15)
  buildings  — procedural generator (05 buildings)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

STUDIO = Path(__file__).resolve().parent
ROOT = STUDIO.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(STUDIO))

from pipeline.blender_runner import run_blender_script  # noqa: E402
from pipeline.config import ensure_asset_dirs, load_config  # noqa: E402
from prompt_parse import parse_brief  # noqa: E402
from prop_templates import suggest_parts  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
_lock = threading.Lock()
_job: dict = {"busy": False, "log": [], "last_error": None, "result": None, "kind": None}
_projects: dict[str, dict] = {}


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", (s or "asset").strip()).strip("_").lower()
    return s or "asset"


def log(msg: str) -> None:
    _job["log"].append(msg)
    if len(_job["log"]) > 500:
        _job["log"] = _job["log"][-500:]
    print(msg, flush=True)


def doctor() -> dict:
    cfg = load_config()
    blender = cfg.get("blender_bin", "blender")
    blender_ok, blender_ver = False, None
    try:
        out = subprocess.check_output([blender, "--version"], text=True, timeout=30)
        blender_ok, blender_ver = True, out.splitlines()[0]
    except Exception as e:
        blender_ver = str(e)
    gpu = "unknown"
    try:
        gpu = (
            subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
                ],
                text=True,
                timeout=20,
            )
            .strip()
            .replace("\n", " | ")
        )
    except Exception:
        pass
    nvidia = "nvidia" in gpu.lower()
    return {
        "blender_ok": blender_ok,
        "blender_version": blender_ver,
        "gpu": gpu,
        "nvidia": nvidia,
        "note": "Prompt or picture → route (prop code / character generator / buildings) → game-ready export.",
    }


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sync(src: Path, kind: str, name: str) -> str | None:
    if not src.exists():
        return None
    dst = STUDIO / "assets" / kind / name / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"assets/{kind}/{name}/{src.name}"


def _preview(path: Path | None, label: str) -> dict | None:
    if path is None or not Path(path).exists():
        return None
    rel = _rel(Path(path))
    if not rel:
        return None
    return {"src": rel, "label": label, "kind": "image" if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else "file"}


def _previews_from_dir(folder: Path, *, glob: str = "*.png", limit: int = 24, prefix: str = "") -> list[dict]:
    if not folder.exists():
        return []
    items = []
    for p in sorted(folder.glob(glob), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        label = f"{prefix}{p.stem}".replace("_", " ")
        item = _preview(p, label)
        if item:
            items.append(item)
    return items


def _with_previews(payload: dict, *groups: list[dict] | None) -> dict:
    seen = set()
    previews: list[dict] = []
    for group in groups:
        for item in group or []:
            if not item or not item.get("src") or item["src"] in seen:
                continue
            seen.add(item["src"])
            previews.append(item)
    # also accept existing list on payload
    for item in payload.get("previews") or []:
        if item.get("src") and item["src"] not in seen:
            seen.add(item["src"])
            previews.append(item)
    payload["previews"] = previews
    return payload


def prop_steps() -> list[dict]:
    return [
        {"id": "refs", "title": "02 · Orthographic refs", "blurb": "One reference → caption → front/side/top with QC loop (or split a real sheet)."},
        {"id": "parts", "title": "03 · parts.json", "blurb": "OpenCV measure + silhouette contour. Approve sizes before build."},
        {"id": "build", "title": "04–05 · Build + assemble", "blurb": "Contour extrude / boxes; render vs ref, fix ≤3 rounds."},
    ]


def character_steps() -> list[dict]:
    return [
        {"id": "sheet", "title": "06 · Turnaround from reference", "blurb": "One concept → caption → front/right/back + QC ≤3."},
        {"id": "generate", "title": "07 · Generate mesh", "blurb": "Hunyuan → TRELLIS → HF TripoSR (demo mesh if all fail)."},
        {"id": "clean", "title": "08 · Clean + bake", "blurb": "Orient, merge, decimate, bake; 5 cm grid renders."},
        {"id": "split", "title": "09 · Tag parts", "blurb": "Head/torso/limbs (+ coat etc.)."},
        {"id": "joints", "title": "10 · Joints", "blurb": "Mixamo joints.json + grid/axis debug."},
        {"id": "weights", "title": "11 · Rig + weights", "blurb": "Armature, cloth bones, max 4 influences."},
        {"id": "pose", "title": "12 · Pose test", "blurb": "Stretch battery; reweight ≤3 rounds."},
        {"id": "clips", "title": "13–14 · Idle + walk + QC", "blurb": "Loops from rest pose; foot-slide report."},
        {"id": "export", "title": "15 · Export FBX/GLB", "blurb": "Apply Transform off, no leaf bones."},
    ]


def _ensure_sheet_views(*, kind: str, name: str, prompt: str, force: bool = False) -> dict:
    """Reference picture or prompt → full sheet with caption + QC correction loop."""
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    from generate_sheet import generate_views  # type: ignore

    def _log(msg: str) -> None:
        log(msg)

    if kind == "character":
        base = ROOT / "examples" / "characters" / name
        out_dir = base / "views"
        has_multi = (out_dir / "view_right.png").exists() and (out_dir / "view_back.png").exists()
        if has_multi and not force:
            return {"skipped": True, "out": str(out_dir)}
        concept = None
        for cand in (out_dir / "concept.png", base / "references" / "concept.png"):
            if cand.exists():
                concept = cand
                break
        design = prompt or (
            (base / "prompt.txt").read_text(encoding="utf-8") if (base / "prompt.txt").exists() else ""
        )
        if not concept and not design.strip():
            raise FileNotFoundError("Need a concept picture or a prompt to build the turnaround")
        log("06 · Reference → turnaround (caption + FLUX + QC ≤3 rounds)…")
        return generate_views(
            kind="character",
            design=design.strip() or "game character",
            out_dir=out_dir,
            concept=concept,
            force=True,
            mode="auto",
            log=_log,
        )

    base = ROOT / "examples" / "props" / name
    out_dir = base / "references"
    has_ortho = (out_dir / "front.png").exists() and (out_dir / "side.png").exists()
    if has_ortho and not force:
        return {"skipped": True, "out": str(out_dir)}
    concept = out_dir / "concept.png" if (out_dir / "concept.png").exists() else None
    design = prompt or (
        (base / "prompt.txt").read_text(encoding="utf-8") if (base / "prompt.txt").exists() else ""
    )
    log("02 · Reference → orthos (caption + FLUX + QC ≤3 rounds)…")
    return generate_views(
        kind="prop",
        design=design.strip() or "game prop",
        out_dir=out_dir,
        concept=concept,
        force=True,
        mode="auto",
        log=_log,
    )


def buildings_steps() -> list[dict]:
    return [
        {"id": "generate", "title": "05 · Procedural buildings", "blurb": "Parametric houses/shops from seeds — not image-to-3D."},
    ]


def start_project(prompt: str, route: str, files: dict[str, bytes], name_override: str | None = None) -> dict:
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    from measure_parts import measure as measure_parts  # type: ignore
    from split_sheet import save_character_views, save_prop_views  # type: ignore

    brief = parse_brief(prompt, route)
    name = slug(name_override or brief["name"])
    route = brief["route"]
    brief["name"] = name

    if route == "prop":
        base = ensure_asset_dirs("props", name)
        (base / "prompt.txt").write_text(prompt, encoding="utf-8")
        (base / "sheet_prompt.txt").write_text(brief["sheet_prompt"], encoding="utf-8")
        ref_map = {
            "front": "front.png",
            "side": "side.png",
            "top": "top.png",
            "image": "concept.png",
            "sheet": "concept.png",
        }
        saved = []
        concept: Path | None = None
        for key, data in files.items():
            if not data:
                continue
            fname = ref_map.get(key, f"{key}.png")
            path = base / "references" / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            saved.append(_rel(path))
            if key in ("image", "sheet"):
                concept = path
        # Only split if the upload is already a multi-panel sheet; else leave as concept.png for FLUX+QC
        if concept and concept.exists() and not (base / "references" / "side.png").exists():
            try:
                from generate_sheet import looks_like_multiview_sheet  # type: ignore

                if looks_like_multiview_sheet(concept):
                    split = save_prop_views(concept, base / "references")
                    saved.extend(split.values())
            except Exception as e:
                log(f"prop sheet split skipped: {e}")

        front = base / "references" / "front.png"
        side = base / "references" / "side.png"
        if side.exists() or front.exists():
            try:
                doc = measure_parts(
                    front=front if front.exists() else None,
                    side=side if side.exists() else None,
                    name=name,
                    width_m=brief["width_m"],
                    depth_m=brief["depth_m"],
                    height_m=brief["height_m"],
                )
            except Exception as e:
                log(f"measure failed ({e}); using template")
                doc = suggest_parts(
                    name=name,
                    kind=brief["prop_kind"],
                    width_m=brief["width_m"],
                    depth_m=brief["depth_m"],
                    height_m=brief["height_m"],
                    notes=prompt,
                )
        else:
            doc = suggest_parts(
                name=name,
                kind=brief["prop_kind"],
                width_m=brief["width_m"],
                depth_m=brief["depth_m"],
                height_m=brief["height_m"],
                notes=prompt,
            )
        (base / "parts.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
        steps = prop_steps()
        project = {
            "name": name,
            "route": route,
            "brief": brief,
            "parts": doc,
            "sheet_prompt": brief["sheet_prompt"],
            "refs": saved,
            "steps": steps,
            "done": [],
            "previews": _previews_from_dir(base / "references", prefix="ref "),
        }
    elif route == "character":
        base = ensure_asset_dirs("characters", name)
        (base / "prompt.txt").write_text(prompt, encoding="utf-8")
        (base / "sheet_prompt.txt").write_text(brief["sheet_prompt"], encoding="utf-8")
        saved = {}
        for key, data in files.items():
            if not data:
                continue
            if key == "glb":
                path = base / "exports" / "raw.glb"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                saved["glb"] = _rel(path)
                continue
            # Default drop = single concept reference (NOT a finished turnaround)
            if key in ("sheet", "image", "concept") or key.startswith("file"):
                path = base / "views" / "concept.png"
            elif key in ("front", "right", "back", "left"):
                path = base / "views" / f"view_{key}.png"
            else:
                path = base / "views" / "concept.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            saved[key] = _rel(path)
        concept = base / "views" / "concept.png"
        if concept.exists():
            try:
                from generate_sheet import looks_like_multiview_sheet  # type: ignore

                if looks_like_multiview_sheet(concept) and not (base / "views" / "view_right.png").exists():
                    split = save_character_views(concept, base / "views")
                    saved.update(split)
                    log("Uploaded file looks like a multi-panel sheet — split into views")
                else:
                    log("Stored as concept.png — turnaround will be generated in step 06 with QC")
            except Exception as e:
                log(f"concept classify note: {e}")
        steps = character_steps()
        project = {
            "name": name,
            "route": route,
            "brief": brief,
            "sheet_prompt": brief["sheet_prompt"],
            "views": saved,
            "steps": steps,
            "done": [],
            "has_raw": (base / "exports" / "raw.glb").exists(),
            "previews": _previews_from_dir(base / "views", prefix=""),
        }
    else:
        base = ensure_asset_dirs("props", "buildings")
        (base / "prompt.txt").write_text(prompt, encoding="utf-8")
        steps = buildings_steps()
        project = {
            "name": "buildings",
            "route": "buildings",
            "brief": brief,
            "count": 5,
            "steps": steps,
            "done": [],
        }

    _projects[name] = project
    (STUDIO / "assets" / "_projects").mkdir(parents=True, exist_ok=True)
    (STUDIO / "assets" / "_projects" / f"{name}.json").write_text(json.dumps(project, indent=2), encoding="utf-8")
    return project


def build_prop(name: str) -> dict:
    name = slug(name)
    base = ensure_asset_dirs("props", name)
    from pipeline.prop_build import build_parts_with_qc

    build_parts_with_qc(name, log=log)
    for glb_part in (base / "parts").glob("*.glb"):
        _sync(glb_part, "prop", name)
    glb = base / "exports" / f"{name}.glb"
    opt = base / "exports" / f"{name}_opt.glb"
    if glb.exists():
        try:
            subprocess.check_call(
                [sys.executable, str(ROOT / "scripts/tools/optimize_gltf.py"), str(glb), "-o", str(opt)],
                cwd=str(ROOT),
            )
        except Exception as e:
            log(f"optimize skipped: {e}")
    studio = _sync(opt if opt.exists() else glb, "prop", name)
    previews = (
        _previews_from_dir(base / "renders", glob="*_vs_ref*.png", prefix="QC ")
        + _previews_from_dir(base / "renders", glob="*_side*.png", prefix="")
        + _previews_from_dir(base / "renders", glob="assemble_*.png", prefix="")
        + _previews_from_dir(base / "references", prefix="ref ")
    )
    return _with_previews(
        {"name": name, "model": _rel(opt if opt.exists() else glb), "studio_model": studio},
        previews,
    )


def generate_character_mesh(name: str) -> Path:
    name = slug(name)
    base = ensure_asset_dirs("characters", name)
    out = base / "exports" / "raw.glb"
    sys.path.insert(0, str(ROOT / "scripts" / "characters"))
    from importlib import import_module

    chain = import_module("07_generate_chain")
    log("07 · Generator chain: Hunyuan → TRELLIS → HF TripoSR")
    try:
        backend = chain.generate(base, out)
    except Exception as e:
        log(f"07 · Generators failed ({e}) — free demo mesh fallback")
        run_blender_script(ROOT / "blender/characters/make_demo_mesh.py", args={"asset": name})
        backend = "demo_mesh"
    if not out.exists():
        run_blender_script(ROOT / "blender/characters/make_demo_mesh.py", args={"asset": name})
        backend = "demo_mesh"
    _sync(out, "character", name)
    log(f"Saved raw.glb via {backend} → {out}")
    return out


def _char_cfg(name: str) -> tuple[Path, dict]:
    base = ensure_asset_dirs("characters", name)
    return base, load_config()["characters"]


def run_character_step(name: str, step_id: str) -> dict:
    """Guide steps 08–15 individually (free Blender path)."""
    name = slug(name)
    base, cfg = _char_cfg(name)
    raw = base / "exports" / "raw.glb"
    if step_id == "clean":
        if not raw.exists():
            raise FileNotFoundError("No raw.glb — run generate first")
        log("08 · Clean + bake")
        run_blender_script(
            ROOT / "blender/characters/clean.py",
            args={"asset": name, "input": str(raw), **{k: cfg[k] for k in ("height_m", "hero_triangles", "crowd_triangles")}},
        )
        clean = base / "exports" / f"{name}_clean.glb"
        return _with_previews(
            {"clean": _rel(clean), "studio_model": _sync(clean, "character", name)},
            _previews_from_dir(base / "renders", glob="clean_*.png", prefix="clean "),
            _previews_from_dir(base / "views", prefix="view "),
        )
    if step_id == "split":
        log("09 · Tag parts")
        run_blender_script(ROOT / "blender/characters/split_parts.py", args={"asset": name})
        return _with_previews(
            {"parts_blend": _rel(base / "exports" / f"{name}_parts.blend"), "studio_model": _sync(base / "exports" / f"{name}_clean.glb", "character", name)},
            _previews_from_dir(base / "renders", glob="*part*.png", prefix="parts "),
            _previews_from_dir(base / "renders", glob="split_*.png", prefix="parts "),
            _previews_from_dir(base / "renders", glob="clean_*.png", prefix="clean "),
        )
    if step_id == "joints":
        log("10 · Joints")
        run_blender_script(ROOT / "blender/characters/joints.py", args={"asset": name})
        return _with_previews(
            {"joints": _rel(base / "exports" / "joints.json"), "studio_model": _sync(base / "exports" / f"{name}_clean.glb", "character", name)},
            _previews_from_dir(base / "renders", glob="joints_*.png", prefix="joints "),
        )
    if step_id == "weights":
        log("11 · Rig + weights")
        run_blender_script(ROOT / "blender/characters/rig_weights.py", args={"asset": name})
        return _with_previews(
            {"rigged": _rel(base / "exports" / f"{name}_rigged.blend"), "studio_model": _sync(base / "exports" / f"{name}_clean.glb", "character", name)},
            _previews_from_dir(base / "renders", glob="joints_*.png", prefix="joints "),
            _previews_from_dir(base / "renders", glob="clean_*.png", prefix="clean "),
        )
    if step_id == "pose":
        log("12 · Pose test (≤3 reweight rounds)")
        for round_i in range(1, 4):
            run_blender_script(
                ROOT / "blender/characters/pose_test.py",
                args={"asset": name, "round": round_i, "fix": True},
            )
            report = json.loads((base / "exports" / "pose_test_report.json").read_text(encoding="utf-8"))
            worst = max((v.get("max_stretch", 1) for v in report.values() if isinstance(v, dict)), default=1)
            log(f"  pose round {round_i}: max_stretch={worst}")
            if worst <= 1.35:
                break
            log("  re-applying weight rules…")
            run_blender_script(ROOT / "blender/characters/rig_weights.py", args={"asset": name})
        return _with_previews(
            {"pose": _rel(base / "exports" / "pose_test_report.json"), "studio_model": _sync(base / "exports" / f"{name}_clean.glb", "character", name)},
            _previews_from_dir(base / "renders", glob="pose_*.png", prefix="pose "),
        )
    if step_id == "clips":
        log("13 · Idle")
        run_blender_script(ROOT / "blender/characters/clips/idle.py", args={"asset": name})
        log("13 · Walk")
        run_blender_script(ROOT / "blender/characters/clips/walk.py", args={"asset": name})
        log("14 · Clip QC")
        run_blender_script(ROOT / "blender/characters/check_clips.py", args={"asset": name})
        # Prefer animated export if present mid-pipeline
        glb_cand = base / "exports" / f"{name}_rigged.glb"
        if not glb_cand.exists():
            glb_cand = base / "exports" / f"{name}_clean.glb"
        return _with_previews(
            {"qc": _rel(base / "exports" / "clip_qc_report.json"), "studio_model": _sync(glb_cand, "character", name) if glb_cand.exists() else None},
            _previews_from_dir(base / "renders", glob="pose_*.png", prefix="pose "),
            _previews_from_dir(base / "renders", glob="clip_*.png", prefix="clip "),
        )
    if step_id == "export":
        log("15 · Export")
        run_blender_script(ROOT / "blender/characters/export_fbx.py", args={"asset": name})
        glb = base / "exports" / f"{name}.glb"
        opt = base / "exports" / f"{name}_opt.glb"
        if glb.exists():
            try:
                subprocess.check_call(
                    [sys.executable, str(ROOT / "scripts/tools/optimize_gltf.py"), str(glb), "-o", str(opt)],
                    cwd=str(ROOT),
                )
            except Exception as e:
                log(f"optimize skipped: {e}")
        studio = _sync(opt if opt.exists() else glb, "character", name)
        return _with_previews(
            {
                "name": name,
                "model": _rel(opt if opt.exists() else glb),
                "studio_model": studio,
                "fbx": _rel(base / "exports" / f"{name}.fbx"),
            },
            _previews_from_dir(base / "renders", glob="*.png", limit=16),
            _previews_from_dir(base / "views", prefix="view "),
        )
    if step_id == "pipeline":
        # backwards compatible: run 08–15
        result = None
        for sid in ("clean", "split", "joints", "weights", "pose", "clips", "export"):
            result = run_character_step(name, sid)
        return result or {}
    raise ValueError(f"Unknown character step {step_id}")


def run_character_pipeline(name: str) -> dict:
    return run_character_step(name, "pipeline")


def run_step(name: str, step_id: str) -> dict:
    proj = _projects.get(name) or json.loads((STUDIO / "assets" / "_projects" / f"{name}.json").read_text(encoding="utf-8"))
    route = proj["route"]
    if route == "prop":
        if step_id == "refs":
            base = ROOT / "examples" / "props" / name
            prompt = (proj.get("brief") or {}).get("prompt") or proj.get("sheet_prompt") or ""
            try:
                info = _ensure_sheet_views(kind="prop", name=name, prompt=prompt)
                if not info.get("skipped"):
                    log(f"02 · FLUX refs ready ({info.get('mode')})")
            except Exception as e:
                log(f"02 · FLUX generate failed ({e}) — using upload/split/template if present")
            refs = list((base / "references").glob("*.png"))
            log(f"02 · {len(refs)} reference file(s)")
            return _with_previews(
                {"studio_model": None, "sheet_prompt": proj.get("sheet_prompt"), "refs": [_rel(r) for r in refs]},
                _previews_from_dir(base / "references", prefix="ref "),
            )
        if step_id == "parts":
            path = ROOT / "examples" / "props" / name / "parts.json"
            base = path.parent
            front, side = base / "references" / "front.png", base / "references" / "side.png"
            if side.exists() or front.exists():
                sys.path.insert(0, str(ROOT / "scripts" / "tools"))
                from measure_parts import measure as measure_parts  # type: ignore

                brief = proj.get("brief") or {}
                doc = measure_parts(
                    front=front if front.exists() else None,
                    side=side if side.exists() else None,
                    name=name,
                    width_m=float(brief.get("width_m", 0.6)),
                    depth_m=float(brief.get("depth_m", 0.6)),
                    height_m=float(brief.get("height_m", 0.5)),
                )
                path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
                log(f"03 · Remeasured parts.json ({len(doc['parts'])} parts) — review & Save before build")
            else:
                doc = json.loads(path.read_text(encoding="utf-8"))
                log("03 · parts.json loaded (template) — review & Save before build")
            proj["parts"] = doc
            proj["parts_approved"] = False
            _projects[name] = proj
            (STUDIO / "assets" / "_projects" / f"{name}.json").write_text(json.dumps(proj, indent=2), encoding="utf-8")
            return _with_previews(
                {"parts": doc, "needs_approval": True},
                _previews_from_dir(base / "references", prefix="measure "),
            )
        if step_id == "build":
            if not proj.get("parts_approved"):
                log("03→04 · Auto-approving parts.json (Save parts to approve explicitly next time)")
                # guide wants OK; Studio run-all still proceeds but marks approval
                proj["parts_approved"] = True
                _projects[name] = proj
            return build_prop(name)
    if route == "character":
        if step_id == "sheet":
            base = ROOT / "examples" / "characters" / name
            views_dir = base / "views"
            prompt = (proj.get("brief") or {}).get("prompt") or ""
            has_multi = (views_dir / "view_right.png").exists() and (views_dir / "view_back.png").exists()
            if not has_multi:
                try:
                    info = _ensure_sheet_views(kind="character", name=name, prompt=prompt, force=True)
                    log(
                        f"06 · sheet done mode={info.get('mode')} backend={info.get('backend')} "
                        f"passed={info.get('passed')} avg={info.get('best_avg')}"
                    )
                    qc = views_dir / "sheet_qc.json"
                    if qc.exists():
                        log(f"06 · QC report → {qc}")
                except Exception as e:
                    log(f"06 · sheet generate failed: {e}")
                    raise
            views = {p.name: _rel(p) for p in views_dir.glob("*.png")}
            log(f"06 · {len(views)} view file(s) ready")
            return _with_previews(
                {
                    "sheet_prompt": proj.get("sheet_prompt"),
                    "views": views,
                    "qc": _rel(views_dir / "sheet_qc.json") if (views_dir / "sheet_qc.json").exists() else None,
                },
                [_preview(views_dir / "concept.png", "concept")] if (views_dir / "concept.png").exists() else [],
                _previews_from_dir(views_dir, prefix=""),
            )
        if step_id == "generate":
            raw = ROOT / "examples" / "characters" / name / "exports" / "raw.glb"
            base = ROOT / "examples" / "characters" / name
            if raw.exists():
                log("07 · Using existing raw.glb")
                return _with_previews(
                    {"raw": _rel(raw), "studio_model": _sync(raw, "character", name)},
                    _previews_from_dir(base / "views", prefix="view "),
                )
            generate_character_mesh(name)
            return _with_previews(
                {"raw": _rel(raw), "studio_model": _sync(raw, "character", name)},
                _previews_from_dir(base / "views", prefix="view "),
            )
        if step_id in ("clean", "split", "joints", "weights", "pose", "clips", "export", "pipeline"):
            return run_character_step(name, step_id)
    if route == "buildings" and step_id == "generate":
        count = int(proj.get("count", 5))
        ensure_asset_dirs("props", "buildings")
        log(f"Buildings × {count}")
        run_blender_script(ROOT / "blender/props/buildings.py", args={"count": count})
        models = []
        for g in sorted((ROOT / "examples" / "props" / "buildings" / "exports").glob("building_*.glb"))[:count]:
            models.append(_sync(g, "prop", "buildings"))
        return {"models": models, "studio_model": models[0] if models else None}
    raise ValueError(f"Unknown step {step_id} for route {route}")


def run_all(name: str) -> dict:
    proj = _projects.get(name) or json.loads((STUDIO / "assets" / "_projects" / f"{name}.json").read_text(encoding="utf-8"))
    result = None
    for step in proj["steps"]:
        result = run_step(name, step["id"])
        proj.setdefault("done", []).append(step["id"])
    return result or {}


def start_job(kind: str, fn) -> None:
    with _lock:
        if _job["busy"]:
            raise RuntimeError("busy")
        _job["busy"] = True
        _job["last_error"] = None
        _job["result"] = None
        _job["kind"] = kind
        _job["log"] = []

    def worker() -> None:
        try:
            _job["result"] = fn()
            log("DONE")
        except Exception as e:
            _job["last_error"] = f"{e}\n{traceback.format_exc()[-2500:]}"
            log(f"ERROR: {e}")
        finally:
            _job["busy"] = False

    threading.Thread(target=worker, daemon=True).start()


def _read_multipart(handler) -> tuple[dict, dict[str, bytes]]:
    ctype = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        length = int(handler.headers.get("Content-Length", "0"))
        raw = handler.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}"), {}
    boundary = None
    for part in ctype.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length)
    fields: dict = {}
    files: dict[str, bytes] = {}
    for chunk in body.split(f"--{boundary}".encode()):
        if not chunk or chunk in (b"--\r\n", b"--"):
            continue
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]
        if b"\r\n\r\n" not in chunk:
            continue
        head, data = chunk.split(b"\r\n\r\n", 1)
        if data.endswith(b"\r\n"):
            data = data[:-2]
        headers = head.decode("utf-8", errors="replace")
        name_m = re.search(r'name="([^"]+)"', headers)
        file_m = re.search(r'filename="([^"]*)"', headers)
        if not name_m:
            continue
        name = name_m.group(1)
        if file_m and file_m.group(1):
            files[name] = data
        else:
            fields[name] = data.decode("utf-8", errors="replace")
    return fields, files


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        if args and "/api/" in str(args[0]):
            print("[studio]", fmt % args)

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._json(200, {"job": {k: _job.get(k) for k in ("busy", "log", "last_error", "result", "kind")}, "doctor": doctor(), "projects": list(_projects.keys())})
            return
        if parsed.path.startswith("/api/project/") and parsed.path.count("/") == 3:
            name = slug(parsed.path.rsplit("/", 1)[-1])
            path = STUDIO / "assets" / "_projects" / f"{name}.json"
            if path.exists():
                self._json(200, json.loads(path.read_text(encoding="utf-8")))
            else:
                self._json(404, {"error": "unknown project"})
            return
        if parsed.path == "/api/file":
            qs = parse_qs(parsed.query)
            rel = (qs.get("path") or [""])[0]
            path = (ROOT / rel).resolve()
            if not str(path).startswith(str(ROOT.resolve())) or not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            suf = path.suffix.lower()
            ctype = {
                ".glb": "model/gltf-binary",
                ".gltf": "model/gltf+json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".json": "application/json",
            }.get(suf, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/project/start":
                fields, files = _read_multipart(self)
                # also accept JSON body fields if no multipart
                if not fields and not files:
                    length = int(self.headers.get("Content-Length", "0"))
                    fields = json.loads((self.rfile.read(length) if length else b"{}").decode() or "{}")
                prompt = fields.get("prompt", "")
                route = fields.get("route", "auto")
                name = fields.get("name") or None
                # normalize file keys from multi upload
                norm_files = {}
                for k, v in files.items():
                    key = k
                    if k.startswith("file"):
                        # guess slot by order
                        key = "image"
                    low = k.lower()
                    if "front" in low:
                        key = "front"
                    elif "right" in low or "side" in low:
                        key = "right" if route == "character" or fields.get("route") == "character" else "side"
                    elif "back" in low:
                        key = "back"
                    elif "top" in low:
                        key = "top"
                    elif low.endswith(".glb") or "glb" in low:
                        key = "glb"
                    norm_files[key] = v
                # single image
                if len(files) == 1 and "image" not in norm_files and "front" not in norm_files and "glb" not in norm_files:
                    norm_files["image"] = next(iter(files.values()))
                project = start_project(prompt, route, norm_files, name)
                self._json(200, project)
                return

            if parsed.path == "/api/project/save-parts":
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads((self.rfile.read(length) if length else b"{}").decode() or "{}")
                name = slug(body.get("name", "prop"))
                doc = body.get("parts") or body
                doc["name"] = name
                path = ensure_asset_dirs("props", name) / "parts.json"
                path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
                if name in _projects:
                    _projects[name]["parts"] = doc
                    _projects[name]["parts_approved"] = True  # guide step 03 OK
                    (STUDIO / "assets" / "_projects" / f"{name}.json").write_text(
                        json.dumps(_projects[name], indent=2), encoding="utf-8"
                    )
                self._json(200, {"ok": True, "path": _rel(path), "parts_approved": True})
                return

            if parsed.path == "/api/project/run":
                if _job["busy"]:
                    self._json(409, {"error": "busy"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads((self.rfile.read(length) if length else b"{}").decode() or "{}")
                name = slug(body.get("name", ""))
                step = body.get("step")
                all_steps = bool(body.get("all"))

                def job():
                    if all_steps:
                        return run_all(name)
                    return run_step(name, step)

                start_job(f"{name}:{step or 'all'}", job)
                self._json(202, {"ok": True})
                return

            self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(500, {"error": str(e), "trace": traceback.format_exc()[-1500:]})


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    info = doctor()
    print(f"Studio → http://{HOST}:{PORT}/")
    print(info["blender_version"], "|", info["gpu"])
    print(info["note"])
    httpd.serve_forever()


if __name__ == "__main__":
    main()
