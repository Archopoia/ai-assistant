#!/usr/bin/env python3
"""Tiny studio server: static UI + optional real Blender step runs."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JOBS: dict[str, dict] = {}
JOB_LOCK = threading.Lock()


def run_cli(args: list[str]) -> dict:
    cmd = [sys.executable, "-m", "pipeline.cli", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-4000:],
        "cmd": " ".join(cmd),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._json({"ok": True, "root": str(ROOT)})
        if parsed.path == "/api/steps":
            return self._json(STEPS)
        if parsed.path.startswith("/api/job/"):
            jid = parsed.path.rsplit("/", 1)[-1]
            with JOB_LOCK:
                job = JOBS.get(jid)
            if not job:
                return self._json({"error": "not found"}, 404)
            return self._json(job)
        if parsed.path in ("/", "/studio", "/studio/"):
            self.path = "/studio/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            data = {}

        if parsed.path == "/api/run":
            route = data.get("route", "prop")
            jid = f"{route}-{int(__import__('time').time())}"
            with JOB_LOCK:
                JOBS[jid] = {"id": jid, "status": "running", "route": route, "log": "Starting…\n"}

            def worker():
                try:
                    if route == "prop":
                        result = run_cli(["prop", "crate"])
                    elif route == "buildings":
                        result = run_cli(["buildings", "--count", "3"])
                    else:
                        result = run_cli(["character", "demo", "--demo"])
                    with JOB_LOCK:
                        JOBS[jid].update(
                            {
                                "status": "done" if result["ok"] else "error",
                                "result": result,
                                "log": (result.get("stdout") or "") + (result.get("stderr") or ""),
                            }
                        )
                except Exception as e:  # noqa: BLE001
                    with JOB_LOCK:
                        JOBS[jid].update({"status": "error", "log": str(e)})

            threading.Thread(target=worker, daemon=True).start()
            return self._json({"id": jid})

        return self._json({"error": "unknown"}, 404)

    def _json(self, payload, code=200):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


# Walkthrough metadata consumed by the UI (relative to pipeline root)
STEPS = {
    "routes": [
        {
            "id": "prop",
            "title": "Prop (crate)",
            "blurb": "Free code path — measure, build parts, assemble, export.",
            "runArgs": ["prop", "crate"],
            "steps": [
                {
                    "id": "p1",
                    "title": "1 · Pick the free prop route",
                    "doing": "Anything you can measure with a ruler → Python in Blender. No paid generator.",
                    "log": [
                        "Route = prop / code",
                        "Units = metres, forward = -Y",
                        "Budget = 2,000 triangles",
                    ],
                    "model": None,
                    "image": "examples/props/crate/renders/assemble_three_quarter.png",
                },
                {
                    "id": "p2",
                    "title": "2 · Write the numbers (parts.json)",
                    "doing": "Before any mesh: size every part and what it attaches to.",
                    "log": [
                        "Read parts.json",
                        "body 0.60 × 0.60 × 0.45 m",
                        "lid + band attach to body",
                    ],
                    "model": None,
                    "image": None,
                    "detail": "examples/props/crate/parts.json",
                },
                {
                    "id": "p3",
                    "title": "3 · Build part: body",
                    "doing": "Blender makes one beveled box from the measurements.",
                    "log": ["bmesh → body", "bevel 2 mm", "export body.glb", "render side QC"],
                    "model": "examples/props/crate/parts/body.glb",
                    "image": "examples/props/crate/renders/body_side.png",
                },
                {
                    "id": "p4",
                    "title": "4 · Build part: lid",
                    "doing": "Next part in a fresh pass — keeps the session small.",
                    "log": ["bmesh → lid", "attaches_to = body", "gap check later"],
                    "model": "examples/props/crate/parts/lid.glb",
                    "image": "examples/props/crate/renders/lid_side.png",
                },
                {
                    "id": "p5",
                    "title": "5 · Build part: band",
                    "doing": "Metal band around the crate — still under the triangle budget.",
                    "log": ["bmesh → band", "flat colour material"],
                    "model": "examples/props/crate/parts/band.glb",
                    "image": "examples/props/crate/renders/band_side.png",
                },
                {
                    "id": "p6",
                    "title": "6 · Assemble + gap check",
                    "doing": "Load all parts, print gaps (must be ~0), join, render views.",
                    "log": [
                        "gap lid → body: 0.00 cm",
                        "gap band → body: 0.00 cm",
                        "triangles: 132 / 2000",
                    ],
                    "model": "examples/props/crate/exports/crate.glb",
                    "image": "examples/props/crate/renders/assemble_three_quarter.png",
                },
                {
                    "id": "p7",
                    "title": "7 · Export for the engine",
                    "doing": "FBX + GLB, then glTF-Transform / meshoptimizer shrink the file.",
                    "log": [
                        "crate.fbx written",
                        "crate.glb → crate_opt.glb",
                        "Ready for Unity / Roblox / web",
                    ],
                    "model": "examples/props/crate/exports/crate_opt.glb",
                    "image": "examples/props/crate/renders/assemble_front.png",
                },
            ],
        },
        {
            "id": "character",
            "title": "Character (demo)",
            "blurb": "Free character path — clean, split, rig, fix clothes stretch, clips, export.",
            "runArgs": ["character", "demo", "--demo"],
            "steps": [
                {
                    "id": "c1",
                    "title": "1 · Mesh in (demo / generator)",
                    "doing": "Start from a free placeholder or a TripoSR / TRELLIS / imported GLB.",
                    "log": ["raw.glb ready", "EU-safe generators only", "Hunyuan skipped"],
                    "model": "examples/characters/demo/exports/raw.glb",
                    "image": None,
                },
                {
                    "id": "c2",
                    "title": "2 · Clean the mesh",
                    "doing": "Face -Y, feet on floor, height 1.15 m, merge verts, hero + crowd LODs.",
                    "log": ["orient + scale", "merge by distance", "hero + crowd exports"],
                    "model": "examples/characters/demo/exports/demo_clean.glb",
                    "image": "examples/characters/demo/renders/clean_front.png",
                },
                {
                    "id": "c3",
                    "title": "3 · Split into body parts",
                    "doing": "Tag head / torso / arms / legs / coat so weights don’t leak.",
                    "log": ["vertex groups by position", "flat colour preview"],
                    "model": "examples/characters/demo/exports/demo_parts.glb",
                    "image": "examples/characters/demo/renders/parts_front.png",
                },
                {
                    "id": "c4",
                    "title": "4 · Place joints",
                    "doing": "Estimate Mixamo joints on a 5 cm mental grid — check before bones.",
                    "log": ["joints.json written", "24 joints", "Hips…ToeBase + coat bones"],
                    "model": "examples/characters/demo/exports/demo_parts.glb",
                    "image": "examples/characters/demo/renders/joints_front.png",
                },
                {
                    "id": "c5",
                    "title": "5 · Rig + clothing weight rules",
                    "doing": "Auto-weights, then zero arm influence on torso/coat; lock hands & head.",
                    "log": [
                        "armature bound",
                        "torso/coat ← no arm bones",
                        "coat skirt → CoatFront/Back",
                        "max 4 influences",
                    ],
                    "model": "examples/characters/demo/exports/demo_clean.glb",
                    "image": "examples/characters/demo/renders/pose_arms_up_90_front.png",
                },
                {
                    "id": "c6",
                    "title": "6 · Pose tests (stretch check)",
                    "doing": "Arms up, step, head turn — print worst stretched edges.",
                    "log": ["arms_up_90 stretch measured", "fix seams if needed", "max 3 rounds"],
                    "model": "examples/characters/demo/exports/demo_clean.glb",
                    "image": "examples/characters/demo/renders/pose_arms_up_90_side.png",
                },
                {
                    "id": "c7",
                    "title": "7 · Idle + walk clips",
                    "doing": "Code the animations on this rest pose; loop first = last frame.",
                    "log": ["idle 2 s @ 30 fps", "walk 1 s, two footsteps", "NLA strips saved"],
                    "model": "examples/characters/demo/exports/demo.glb",
                    "image": "examples/characters/demo/renders/clip_walk_mid.png",
                },
                {
                    "id": "c8",
                    "title": "8 · Export FBX for the engine",
                    "doing": "Apply Transform OFF, leaf bones OFF, probe cube for scale check.",
                    "log": ["demo.fbx", "24 bones", "Unity Humanoid / Roblox Custom"],
                    "model": "examples/characters/demo/exports/demo_opt.glb",
                    "image": "examples/characters/demo/renders/clip_idle_mid.png",
                },
            ],
        },
    ]
}


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Studio → http://127.0.0.1:{port}/studio/", flush=True)
    print(f"API    → http://127.0.0.1:{port}/api/steps", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
