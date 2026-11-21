#!/usr/bin/env python3
"""
Local-only 3D Pipeline Studio server (127.0.0.1).

Runs real Blender pipeline steps and serves the Studio UI + GLBs.
"""
from __future__ import annotations

import json
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.blender_runner import run_blender_script  # noqa: E402
from pipeline.config import ensure_asset_dirs, load_config  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
_lock = threading.Lock()
_job: dict = {"busy": False, "log": [], "last_error": None, "mode": None, "step": None}


def log(msg: str) -> None:
    _job["log"].append(msg)
    if len(_job["log"]) > 400:
        _job["log"] = _job["log"][-400:]
    print(msg, flush=True)


def doctor() -> dict:
    cfg = load_config()
    blender = cfg.get("blender_bin", "blender")
    blender_ok = False
    blender_ver = None
    try:
        out = subprocess.check_output([blender, "--version"], text=True, timeout=30)
        blender_ok = True
        blender_ver = out.splitlines()[0]
    except Exception as e:
        blender_ver = str(e)

    gpu = "unknown"
    try:
        import subprocess as sp

        ps = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object -ExpandProperty Name"
        )
        names = sp.check_output(
            ["powershell", "-NoProfile", "-Command", ps], text=True, timeout=20
        ).strip()
        gpu = names.replace("\n", " | ") or "unknown"
    except Exception:
        pass

    nvidia = "nvidia" in gpu.lower()
    return {
        "blender_ok": blender_ok,
        "blender": blender,
        "blender_version": blender_ver,
        "gpu": gpu,
        "nvidia": nvidia,
        "generator": cfg.get("characters", {}).get("generator", "import"),
        "note": (
            "TRELLIS needs NVIDIA CUDA. This machine can run props + demo character "
            "via Blender. Drop a GLB or get an NVIDIA GPU for local image→mesh."
            if not nvidia
            else "NVIDIA detected — you can run .\\scripts\\install_trellis.ps1"
        ),
    }


def run_prop_step(index: int) -> dict:
    name = "crate"
    base = ensure_asset_dirs("props", name)
    parts_doc = json.loads((base / "parts.json").read_text(encoding="utf-8"))
    part_names = [p["name"] for p in parts_doc["parts"]]

    if index < len(part_names):
        part = part_names[index]
        log(f"Building part: {part}")
        run_blender_script(
            ROOT / "blender/props/build_part.py",
            args={"asset": name, "part": part, "render_px": 768},
        )
        # Prefer per-part export if present; else parts folder blend/glb naming varies
        candidates = [
            base / "parts" / f"{part}.glb",
            base / "exports" / f"{part}.glb",
        ]
        model = next((c for c in candidates if c.exists()), None)
        return {"title": f"Build {part}", "model": _rel(model) if model else None}

    if index == len(part_names):
        log("Assembling crate + export")
        run_blender_script(ROOT / "blender/props/assemble.py", args={"asset": name})
        model = base / "exports" / f"{name}.glb"
        return {"title": "Assemble", "model": _rel(model) if model.exists() else None}

    # optimize
    glb = base / "exports" / f"{name}.glb"
    opt = base / "exports" / f"{name}_opt.glb"
    if glb.exists():
        log("Optimizing GLB")
        subprocess.check_call(
            [sys.executable, str(ROOT / "scripts/tools/optimize_gltf.py"), str(glb), "-o", str(opt)],
            cwd=str(ROOT),
        )
    return {"title": "Optimize", "model": _rel(opt if opt.exists() else glb)}


def run_character_step(index: int) -> dict:
    name = "demo"
    base = ensure_asset_dirs("characters", name)
    raw = base / "exports" / "raw.glb"
    cfg = load_config()["characters"]

    steps = [
        ("demo", None, {"asset": name}, "blender/characters/make_demo_mesh.py", "raw.glb"),
        (
            "clean",
            {"asset": name, "input": str(raw), **{k: cfg[k] for k in ("height_m", "hero_triangles", "crowd_triangles")}},
            None,
            "blender/characters/clean.py",
            "demo_clean.glb",
        ),
        ("split", {"asset": name}, None, "blender/characters/split_parts.py", "demo_parts.glb"),
        ("joints", {"asset": name}, None, "blender/characters/joints.py", "demo_parts.glb"),
        ("rig", {"asset": name}, None, "blender/characters/rig_weights.py", "demo.glb"),
        ("pose", {"asset": name}, None, "blender/characters/pose_test.py", "demo.glb"),
        ("idle", {"asset": name}, None, "blender/characters/clips/idle.py", "demo.glb"),
        ("walk", {"asset": name}, None, "blender/characters/clips/walk.py", "demo.glb"),
        ("qc", {"asset": name}, None, "blender/characters/check_clips.py", "demo.glb"),
        ("export", {"asset": name}, None, "blender/characters/export_fbx.py", "demo.glb"),
        ("optimize", None, None, None, "demo_opt.glb"),
    ]
    if index < 0 or index >= len(steps):
        raise ValueError(f"character step out of range: {index}")

    key, args, _legacy, script, model_name = steps[index]
    log(f"Character step: {key}")

    if key == "demo":
        run_blender_script(ROOT / "blender/characters/make_demo_mesh.py", args={"asset": name})
    elif key == "optimize":
        glb = base / "exports" / "demo.glb"
        opt = base / "exports" / "demo_opt.glb"
        if glb.exists():
            subprocess.check_call(
                [
                    sys.executable,
                    str(ROOT / "scripts/tools/optimize_gltf.py"),
                    str(glb),
                    "-o",
                    str(opt),
                ],
                cwd=str(ROOT),
            )
    else:
        run_blender_script(ROOT / script, args=args)

    model = base / "exports" / model_name
    # After demo, copy into studio assets for convenience
    if model.exists():
        dst = STUDIO / "assets" / "character" / model.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model, dst)
    return {"title": key, "model": _rel(model) if model.exists() else None}


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def run_job(mode: str, step: int | None, run_all: bool) -> None:
    with _lock:
        if _job["busy"]:
            return
        _job["busy"] = True
        _job["last_error"] = None
        _job["mode"] = mode
        _job["step"] = step
        _job["log"] = []

    def worker() -> None:
        try:
            if mode == "prop":
                n = 5  # 3 parts + assemble + optimize (dynamic length based on parts.json)
                parts = json.loads(
                    (ensure_asset_dirs("props", "crate") / "parts.json").read_text(encoding="utf-8")
                )["parts"]
                total = len(parts) + 2
                indices = range(total) if run_all else [int(step)]
                result = None
                for i in indices:
                    result = run_prop_step(i)
                    # sync into studio assets
                    if result.get("model"):
                        src = ROOT / result["model"]
                        if src.exists() and src.suffix.lower() == ".glb":
                            dst = STUDIO / "assets" / "prop" / src.name
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dst)
                            result["studio_model"] = f"assets/prop/{src.name}"
                _job["result"] = result
            elif mode == "character":
                total = 11
                indices = range(total) if run_all else [int(step)]
                result = None
                for i in indices:
                    result = run_character_step(i)
                    if result.get("model"):
                        name = Path(result["model"]).name
                        result["studio_model"] = f"assets/character/{name}"
                _job["result"] = result
            else:
                raise ValueError(f"unknown mode {mode}")
            log("DONE")
        except Exception as e:
            _job["last_error"] = f"{e}\n{traceback.format_exc()[-2000:]}"
            log(f"ERROR: {e}")
        finally:
            _job["busy"] = False

    threading.Thread(target=worker, daemon=True).start()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        if args and str(args[0]).startswith(("/api/",)):
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
            self._json(200, {"job": {k: _job[k] for k in ("busy", "log", "last_error", "mode", "step", "result") if k in _job}, "doctor": doctor()})
            return
        if parsed.path == "/api/file":
            qs = parse_qs(parsed.query)
            rel = (qs.get("path") or [""])[0]
            path = (ROOT / rel).resolve()
            if not str(path).startswith(str(ROOT.resolve())) or not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            ctype = "model/gltf-binary" if path.suffix.lower() == ".glb" else "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return

        if parsed.path == "/api/run":
            if _job["busy"]:
                self._json(409, {"error": "busy", "job": _job})
                return
            mode = payload.get("mode", "prop")
            run_all = bool(payload.get("all"))
            step = payload.get("step")
            run_job(mode, step, run_all)
            self._json(202, {"ok": True, "started": True})
            return

        if parsed.path == "/api/reset-log":
            _job["log"] = []
            _job["last_error"] = None
            self._json(200, {"ok": True})
            return

        self._json(404, {"error": "not found"})


def main() -> None:
    # Bind localhost only — intentional local app, not cloud.
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    info = doctor()
    print(f"Studio → http://{HOST}:{PORT}/")
    print(f"Blender: {info['blender_version']} ({'OK' if info['blender_ok'] else 'MISSING'})")
    print(f"GPU: {info['gpu']}")
    print(info["note"])
    httpd.serve_forever()


if __name__ == "__main__":
    main()
