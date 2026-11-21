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


def prop_steps() -> list[dict]:
    return [
        {"id": "refs", "title": "02 · Orthographic refs", "blurb": "Generate front/side/top via free HF FLUX, or split an uploaded sheet."},
        {"id": "parts", "title": "03 · parts.json", "blurb": "OpenCV measure + silhouette contour. Approve sizes before build."},
        {"id": "build", "title": "04–05 · Build + assemble", "blurb": "Contour extrude / boxes in Blender, then assemble + export."},
    ]


def character_steps() -> list[dict]:
    return [
        {"id": "sheet", "title": "06 · Turnaround sheet", "blurb": "Generate front/right/back via free HF FLUX from prompt (or split upload)."},
        {"id": "generate", "title": "07 · Generate mesh", "blurb": "Hunyuan → TRELLIS → HF TripoSR (or drop GLB)."},
        {"id": "pipeline", "title": "08–15 · Clean → rig → clips → export", "blurb": "Bake maps when possible, then Mixamo-style free pipeline."},
    ]


def _ensure_sheet_views(*, kind: str, name: str, prompt: str, force: bool = False) -> dict:
    """Create missing orthographic / turnaround images with HF FLUX when needed."""
    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    from generate_sheet import generate_views  # type: ignore

    if kind == "character":
        base = ROOT / "examples" / "characters" / name
        out_dir = base / "views"
        has_multi = (out_dir / "view_right.png").exists() or (out_dir / "view_back.png").exists()
        if has_multi and not force:
            return {"skipped": True, "out": str(out_dir)}
        concept = None
        for cand in (out_dir / "concept.png", base / "references" / "concept.png"):
            if cand.exists():
                concept = cand
                break
        design = prompt or (
            (base / "prompt.txt").read_text(encoding="utf-8") if (base / "prompt.txt").exists() else "game character"
        )
        log("06 · Generating turnaround via HF FLUX.1-schnell (free)…")
        return generate_views(
            kind="character",
            design=design.strip(),
            out_dir=out_dir,
            concept=concept,
            force=True,
            mode="panels",
        )

    base = ROOT / "examples" / "props" / name
    out_dir = base / "references"
    has_ortho = (out_dir / "front.png").exists() and (out_dir / "side.png").exists()
    if has_ortho and not force:
        return {"skipped": True, "out": str(out_dir)}
    concept = out_dir / "concept.png" if (out_dir / "concept.png").exists() else None
    design = prompt or (
        (base / "prompt.txt").read_text(encoding="utf-8") if (base / "prompt.txt").exists() else "game prop"
    )
    log("02 · Generating orthographic refs via HF FLUX.1-schnell (free)…")
    return generate_views(
        kind="prop",
        design=design.strip(),
        out_dir=out_dir,
        concept=concept,
        force=True,
        mode="panels",
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
        # Split a single concept sheet into front/side/top when needed
        if concept and concept.exists() and not (base / "references" / "side.png").exists():
            try:
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
        }
    elif route == "character":
        base = ensure_asset_dirs("characters", name)
        (base / "prompt.txt").write_text(prompt, encoding="utf-8")
        (base / "sheet_prompt.txt").write_text(brief["sheet_prompt"], encoding="utf-8")
        saved = {}
        concept: Path | None = None
        for key, data in files.items():
            if not data:
                continue
            if key == "glb":
                path = base / "exports" / "raw.glb"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                saved["glb"] = _rel(path)
                continue
            slot = "front" if key in ("sheet", "image") else key
            path = base / "views" / f"view_{slot}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            saved[key] = _rel(path)
            if key in ("sheet", "image"):
                concept = path
        if concept and concept.exists() and not (base / "views" / "view_right.png").exists():
            try:
                split = save_character_views(concept, base / "views")
                saved.update(split)
            except Exception as e:
                log(f"character sheet split skipped: {e}")
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
    parts_path = base / "parts.json"
    doc = json.loads(parts_path.read_text(encoding="utf-8"))
    for part in doc["parts"]:
        log(f"04 · Build part “{part['name']}”")
        run_blender_script(
            ROOT / "blender/props/build_part.py",
            args={"asset": name, "part": part["name"], "render_px": 768},
        )
        _sync(base / "parts" / f"{part['name']}.glb", "prop", name)
    log("05 · Assemble + export")
    run_blender_script(ROOT / "blender/props/assemble.py", args={"asset": name})
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
    return {"name": name, "model": _rel(opt if opt.exists() else glb), "studio_model": studio}


def generate_character_mesh(name: str) -> Path:
    name = slug(name)
    base = ensure_asset_dirs("characters", name)
    out = base / "exports" / "raw.glb"
    sys.path.insert(0, str(ROOT / "scripts" / "characters"))
    from importlib import import_module

    chain = import_module("07_generate_chain")
    log("07 · Generator chain: Hunyuan → TRELLIS → HF TripoSR")
    backend = chain.generate(base, out)
    _sync(out, "character", name)
    log(f"Saved raw.glb via {backend} → {out}")
    return out


def run_character_pipeline(name: str) -> dict:
    name = slug(name)
    base = ensure_asset_dirs("characters", name)
    raw = base / "exports" / "raw.glb"
    if not raw.exists():
        raise FileNotFoundError("No raw.glb — run generate (step 07) or upload a GLB")
    cfg = load_config()["characters"]
    steps = [
        ("08 clean", "blender/characters/clean.py", {"asset": name, "input": str(raw), **{k: cfg[k] for k in ("height_m", "hero_triangles", "crowd_triangles")}}),
        ("09 split", "blender/characters/split_parts.py", {"asset": name}),
        ("10 joints", "blender/characters/joints.py", {"asset": name}),
        ("11 weights", "blender/characters/rig_weights.py", {"asset": name}),
        ("12 pose", "blender/characters/pose_test.py", {"asset": name}),
        ("13 idle", "blender/characters/clips/idle.py", {"asset": name}),
        ("13 walk", "blender/characters/clips/walk.py", {"asset": name}),
        ("14 qc", "blender/characters/check_clips.py", {"asset": name}),
        ("15 export", "blender/characters/export_fbx.py", {"asset": name}),
    ]
    for label, script, args in steps:
        log(label)
        run_blender_script(ROOT / script, args=args)
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
    return {"name": name, "model": _rel(opt if opt.exists() else glb), "studio_model": studio, "fbx": _rel(base / "exports" / f"{name}.fbx")}


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
            return {"studio_model": None, "sheet_prompt": proj.get("sheet_prompt"), "refs": [_rel(r) for r in refs]}
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
                log(f"03 · Remeasured parts.json ({len(doc['parts'])} parts, contour where possible)")
            else:
                doc = json.loads(path.read_text(encoding="utf-8"))
                log("03 · parts.json loaded (no refs — template / prompt sizes)")
            return {"parts": doc}
        if step_id == "build":
            return build_prop(name)
    if route == "character":
        if step_id == "sheet":
            base = ROOT / "examples" / "characters" / name
            views_dir = base / "views"
            prompt = (proj.get("brief") or {}).get("prompt") or proj.get("sheet_prompt") or ""
            # Prefer generating a real turnaround when we only have prompt / single concept
            has_multi = (views_dir / "view_right.png").exists() or (views_dir / "view_back.png").exists()
            concept_only = (views_dir / "concept.png").exists() or (
                (views_dir / "view_front.png").exists() and not has_multi
            )
            if not has_multi:
                try:
                    info = _ensure_sheet_views(kind="character", name=name, prompt=prompt, force=bool(concept_only or prompt))
                    if not info.get("skipped"):
                        log(f"06 · FLUX turnaround ready ({info.get('mode')}, {len(info.get('saved') or {})} files)")
                except Exception as e:
                    log(f"06 · FLUX generate failed ({e}) — trying split of uploaded sheet")
                    for cand in (views_dir / "concept.png", views_dir / "view_front.png", base / "references" / "concept.png"):
                        if cand.exists():
                            sys.path.insert(0, str(ROOT / "scripts" / "tools"))
                            from split_sheet import save_character_views  # type: ignore

                            try:
                                save_character_views(cand, views_dir)
                                log("06 · Split uploaded sheet into front/right/back")
                            except Exception as e2:
                                log(f"sheet split note: {e2}")
                            break
            views = {p.name: _rel(p) for p in views_dir.glob("*.png")}
            log(f"06 · {len(views)} view file(s) ready")
            return {"sheet_prompt": proj.get("sheet_prompt"), "views": views}
        if step_id == "generate":
            raw = ROOT / "examples" / "characters" / name / "exports" / "raw.glb"
            if raw.exists():
                log("07 · Using existing raw.glb")
                return {"raw": _rel(raw), "studio_model": _sync(raw, "character", name)}
            generate_character_mesh(name)
            return {"raw": _rel(ROOT / "examples" / "characters" / name / "exports" / "raw.glb")}
        if step_id == "pipeline":
            return run_character_pipeline(name)
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
            self.send_response(200)
            self.send_header("Content-Type", "model/gltf-binary" if path.suffix.lower() == ".glb" else "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
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
                self._json(200, {"ok": True, "path": _rel(path)})
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
