#!/usr/bin/env python3
"""
Local creator Studio — tutorial workflow on this PC (127.0.0.1 only).

Props: name + sizes/template → parts.json → Blender build → assemble → GLB/FBX
Characters: upload photos → free TripoSR (HF Space) or import GLB → clean→rig→clips
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
from prop_templates import suggest_parts  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
_lock = threading.Lock()
_job: dict = {
    "busy": False,
    "log": [],
    "last_error": None,
    "result": None,
    "kind": None,
}


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
        "blender": blender,
        "blender_version": blender_ver,
        "gpu": gpu,
        "nvidia": nvidia,
        "triposr": "huggingface://stabilityai/TripoSR (free ZeroGPU)",
        "note": (
            "Props: measured parts → Blender (local). "
            "Characters: photo → free TripoSR on Hugging Face, then Blender rig. "
            + ("Local TRELLIS available (NVIDIA)." if nvidia else "No NVIDIA — TripoSR uses HF Space.")
        ),
    }


def list_assets() -> dict:
    props, chars = [], []
    pdir = ROOT / "examples" / "props"
    cdir = ROOT / "examples" / "characters"
    if pdir.is_dir():
        for d in sorted(pdir.iterdir()):
            if d.is_dir() and (d / "parts.json").exists():
                glb = d / "exports" / f"{d.name}.glb"
                props.append({"name": d.name, "glb": _rel(glb) if glb.exists() else None})
    if cdir.is_dir():
        for d in sorted(cdir.iterdir()):
            if d.is_dir():
                glb = d / "exports" / f"{d.name}.glb"
                raw = d / "exports" / "raw.glb"
                chars.append(
                    {
                        "name": d.name,
                        "glb": _rel(glb) if glb.exists() else None,
                        "raw": _rel(raw) if raw.exists() else None,
                    }
                )
    return {"props": props, "characters": chars}


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sync_studio(src: Path, kind: str, name: str) -> str | None:
    if not src.exists():
        return None
    dst = STUDIO / "assets" / kind / name / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"assets/{kind}/{name}/{src.name}"


def build_prop(name: str) -> dict:
    name = slug(name)
    base = ensure_asset_dirs("props", name)
    parts_path = base / "parts.json"
    if not parts_path.exists():
        raise FileNotFoundError(f"Missing {parts_path} — create parts first")
    doc = json.loads(parts_path.read_text(encoding="utf-8"))
    models = []
    for part in doc["parts"]:
        log(f"Build part “{part['name']}”…")
        run_blender_script(
            ROOT / "blender/props/build_part.py",
            args={"asset": name, "part": part["name"], "render_px": 768},
        )
        glb = base / "parts" / f"{part['name']}.glb"
        models.append(_sync_studio(glb, "prop", name))
    log("Assemble + export FBX/GLB…")
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
    studio = _sync_studio(opt if opt.exists() else glb, "prop", name)
    return {
        "name": name,
        "model": _rel(opt if opt.exists() else glb),
        "studio_model": studio,
        "parts": models,
        "report": _rel(base / "exports" / "assemble_report.json"),
    }


def generate_character_mesh(name: str, front: Path, right: Path | None = None, back: Path | None = None) -> Path:
    """Free image→mesh via Hugging Face TripoSR Space (no local NVIDIA needed)."""
    name = slug(name)
    base = ensure_asset_dirs("characters", name)
    out = base / "exports" / "raw.glb"
    out.parent.mkdir(parents=True, exist_ok=True)

    log("Calling free TripoSR on Hugging Face (stabilityai/TripoSR)…")
    try:
        from gradio_client import Client, handle_file
    except ImportError as e:
        raise RuntimeError("pip install gradio_client") from e

    client = Client("stabilityai/TripoSR")
    # Single-image feed-forward; use front (best for A-pose sheet). Extra views saved for later.
    result = client.predict(
        handle_file(str(front)),
        True,  # remove background
        0.85,  # foreground ratio
        256,  # mc resolution
        api_name="/generate",
    )
    # result typically [obj_path, glb_path] or similar
    glb_src = None
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, str) and item.lower().endswith(".glb"):
                glb_src = item
                break
            if isinstance(item, dict) and str(item.get("path", "")).lower().endswith(".glb"):
                glb_src = item["path"]
                break
    elif isinstance(result, str) and result.lower().endswith(".glb"):
        glb_src = result
    if not glb_src or not Path(glb_src).exists():
        raise RuntimeError(f"TripoSR returned no GLB: {result!r}")
    shutil.copy2(glb_src, out)
    log(f"Saved raw mesh → {out}")
    _sync_studio(out, "character", name)
    return out


def run_character_pipeline(name: str) -> dict:
    name = slug(name)
    base = ensure_asset_dirs("characters", name)
    raw = base / "exports" / "raw.glb"
    if not raw.exists():
        raise FileNotFoundError("No raw.glb — generate from photo or upload a GLB first")
    cfg = load_config()["characters"]
    steps = [
        (
            "clean",
            "blender/characters/clean.py",
            {
                "asset": name,
                "input": str(raw),
                **{k: cfg[k] for k in ("height_m", "hero_triangles", "crowd_triangles")},
            },
        ),
        ("split", "blender/characters/split_parts.py", {"asset": name}),
        ("joints", "blender/characters/joints.py", {"asset": name}),
        ("rig", "blender/characters/rig_weights.py", {"asset": name}),
        ("pose", "blender/characters/pose_test.py", {"asset": name}),
        ("idle", "blender/characters/clips/idle.py", {"asset": name}),
        ("walk", "blender/characters/clips/walk.py", {"asset": name}),
        ("qc", "blender/characters/check_clips.py", {"asset": name}),
        ("export", "blender/characters/export_fbx.py", {"asset": name}),
    ]
    for key, script, args in steps:
        log(f"Character · {key}")
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
    studio = _sync_studio(opt if opt.exists() else glb, "character", name)
    return {
        "name": name,
        "model": _rel(opt if opt.exists() else glb),
        "studio_model": studio,
        "fbx": _rel(base / "exports" / f"{name}.fbx"),
    }


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


def _read_json(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def _read_multipart(handler: SimpleHTTPRequestHandler) -> tuple[dict, dict[str, bytes]]:
    """Minimal multipart parser for file uploads."""
    ctype = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        return _read_json(handler), {}
    boundary = None
    for part in ctype.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
    if not boundary:
        raise ValueError("no multipart boundary")
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
        if not name_m:
            continue
        name = name_m.group(1)
        if "filename=" in headers:
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
            self._json(
                200,
                {
                    "job": {
                        k: _job.get(k)
                        for k in ("busy", "log", "last_error", "result", "kind")
                    },
                    "doctor": doctor(),
                    "assets": list_assets(),
                },
            )
            return
        if parsed.path == "/api/file":
            qs = parse_qs(parsed.query)
            rel = (qs.get("path") or [""])[0]
            path = (ROOT / rel).resolve()
            if not str(path).startswith(str(ROOT.resolve())) or not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            ctype = (
                "model/gltf-binary"
                if path.suffix.lower() == ".glb"
                else "application/json"
                if path.suffix.lower() == ".json"
                else "application/octet-stream"
            )
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path.startswith("/api/parts/"):
            name = slug(parsed.path.rsplit("/", 1)[-1])
            path = ROOT / "examples" / "props" / name / "parts.json"
            if not path.exists():
                self._json(404, {"error": "not found"})
                return
            self._json(200, json.loads(path.read_text(encoding="utf-8")))
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/prop/suggest":
                body = _read_json(self)
                doc = suggest_parts(
                    name=slug(body.get("name", "prop")),
                    kind=body.get("kind", "crate"),
                    width_m=float(body.get("width_m", 0.6)),
                    depth_m=float(body.get("depth_m", 0.6)),
                    height_m=float(body.get("height_m", 0.5)),
                    notes=body.get("notes", ""),
                )
                self._json(200, doc)
                return

            if parsed.path == "/api/prop/save":
                body = _read_json(self)
                name = slug(body.get("name") or body.get("parts", {}).get("name", "prop"))
                doc = body.get("parts") or body
                doc["name"] = name
                base = ensure_asset_dirs("props", name)
                path = base / "parts.json"
                path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
                self._json(200, {"ok": True, "name": name, "path": _rel(path)})
                return

            if parsed.path == "/api/prop/build":
                if _job["busy"]:
                    self._json(409, {"error": "busy"})
                    return
                body = _read_json(self)
                name = slug(body.get("name", "prop"))
                start_job("prop", lambda: build_prop(name))
                self._json(202, {"ok": True})
                return

            if parsed.path == "/api/prop/upload-refs":
                fields, files = _read_multipart(self)
                name = slug(fields.get("name", "prop"))
                base = ensure_asset_dirs("props", name)
                saved = []
                for key, data in files.items():
                    if not data:
                        continue
                    fname = key if key.endswith(".png") else f"{key}.png"
                    path = base / "references" / fname
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    saved.append(_rel(path))
                self._json(200, {"ok": True, "name": name, "saved": saved})
                return

            if parsed.path == "/api/character/upload":
                fields, files = _read_multipart(self)
                name = slug(fields.get("name", "hero"))
                base = ensure_asset_dirs("characters", name)
                saved = {}
                for key in ("front", "right", "back", "glb"):
                    if key not in files or not files[key]:
                        continue
                    if key == "glb":
                        path = base / "exports" / "raw.glb"
                    else:
                        path = base / "views" / f"view_{key}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(files[key])
                    saved[key] = _rel(path)
                    if key != "glb":
                        # also keep generic names
                        pass
                self._json(200, {"ok": True, "name": name, "saved": saved})
                return

            if parsed.path == "/api/character/generate":
                if _job["busy"]:
                    self._json(409, {"error": "busy"})
                    return
                body = _read_json(self)
                name = slug(body.get("name", "hero"))
                base = ensure_asset_dirs("characters", name)
                front = base / "views" / "view_front.png"
                if not front.exists():
                    # accept any uploaded front
                    alts = list((base / "views").glob("*front*")) + list((base / "views").glob("*.png"))
                    if alts:
                        front = alts[0]
                if not front.exists():
                    self._json(400, {"error": "Upload a front view photo first"})
                    return
                right = base / "views" / "view_right.png"
                back = base / "views" / "view_back.png"

                def job():
                    generate_character_mesh(
                        name,
                        front,
                        right if right.exists() else None,
                        back if back.exists() else None,
                    )
                    return {"name": name, "raw": _rel(base / "exports" / "raw.glb")}

                start_job("character_generate", job)
                self._json(202, {"ok": True})
                return

            if parsed.path == "/api/character/pipeline":
                if _job["busy"]:
                    self._json(409, {"error": "busy"})
                    return
                body = _read_json(self)
                name = slug(body.get("name", "hero"))
                start_job("character_pipeline", lambda: run_character_pipeline(name))
                self._json(202, {"ok": True})
                return

            if parsed.path == "/api/buildings":
                if _job["busy"]:
                    self._json(409, {"error": "busy"})
                    return
                body = _read_json(self)
                count = int(body.get("count", 3))

                def job():
                    ensure_asset_dirs("props", "buildings")
                    log(f"Procedural buildings × {count}")
                    run_blender_script(ROOT / "blender/props/buildings.py", args={"count": count})
                    out = ROOT / "examples" / "props" / "buildings" / "exports"
                    models = []
                    for g in sorted(out.glob("building_*.glb"))[:count]:
                        models.append(_sync_studio(g, "prop", "buildings"))
                    return {"models": models}

                start_job("buildings", job)
                self._json(202, {"ok": True})
                return

            self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(500, {"error": str(e), "trace": traceback.format_exc()[-1500:]})


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    info = doctor()
    print(f"Studio → http://{HOST}:{PORT}/")
    print(f"Blender: {info['blender_version']} ({'OK' if info['blender_ok'] else 'MISSING'})")
    print(f"GPU: {info['gpu']}")
    print(info["note"])
    httpd.serve_forever()


if __name__ == "__main__":
    main()
