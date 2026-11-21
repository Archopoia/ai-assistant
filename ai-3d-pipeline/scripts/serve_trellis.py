#!/usr/bin/env python3
"""
Local TRELLIS HTTP server for the free pipeline.

POST /multiview  multipart: front[, right, back]  → GLB bytes
GET  /health     → {"ok": true, "model": "..."}

Expects conda env `trellis` with TRELLIS installed
(Windows: scripts/install_trellis.ps1 — Linux: scripts/install_trellis.sh).
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SPCONV_ALGO", "native")
# flash-attn often missing on Windows; xformers is the reliable default there
os.environ.setdefault("ATTN_BACKEND", "xformers")

from flask import Flask, jsonify, request

TRELLIS_ROOT = Path(
    os.environ.get(
        "TRELLIS_ROOT",
        Path(__file__).resolve().parents[1] / "third_party" / "repos" / "TRELLIS",
    )
)
sys.path.insert(0, str(TRELLIS_ROOT))

from PIL import Image  # noqa: E402
from trellis.pipelines import TrellisImageTo3DPipeline  # noqa: E402
from trellis.utils import postprocessing_utils  # noqa: E402

MODEL_ID = os.environ.get("TRELLIS_MODEL", "microsoft/TRELLIS-image-large")
HOST = os.environ.get("TRELLIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("TRELLIS_PORT", "8090"))
SEED = int(os.environ.get("TRELLIS_SEED", "1"))

app = Flask(__name__)
pipeline = None


def get_pipeline():
    global pipeline
    if pipeline is None:
        print(f"Loading {MODEL_ID} …")
        pipeline = TrellisImageTo3DPipeline.from_pretrained(MODEL_ID)
        pipeline.cuda()
        print("TRELLIS ready")
    return pipeline


def _pil_from_storage(storage) -> Image.Image:
    return Image.open(io.BytesIO(storage.read())).convert("RGBA")


def images_to_glb(images: list[Image.Image]) -> bytes:
    pipe = get_pipeline()
    if len(images) == 1:
        outputs = pipe.run(images[0], seed=SEED)
    else:
        outputs = pipe.run_multi_image(
            images,
            seed=SEED,
            sparse_structure_sampler_params={"steps": 12, "cfg_strength": 7.5},
            slat_sampler_params={"steps": 12, "cfg_strength": 3},
        )
    glb = postprocessing_utils.to_glb(
        outputs["gaussian"][0],
        outputs["mesh"][0],
        simplify=0.95,
        texture_size=1024,
    )
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
        path = tmp.name
    try:
        glb.export(path)
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


@app.get("/health")
def health():
    return jsonify(ok=True, model=MODEL_ID, root=str(TRELLIS_ROOT))


@app.post("/multiview")
def multiview():
    if "front" not in request.files:
        return jsonify(error="front image required"), 400
    images = [_pil_from_storage(request.files["front"])]
    for key in ("right", "back"):
        if key in request.files and request.files[key].filename:
            images.append(_pil_from_storage(request.files[key]))
    data = images_to_glb(images)
    return app.response_class(data, mimetype="model/gltf-binary")


def main() -> None:
    if not TRELLIS_ROOT.is_dir():
        raise SystemExit(f"TRELLIS not found at {TRELLIS_ROOT}. Run scripts/install_trellis.sh")
    get_pipeline()
    app.run(host=HOST, port=PORT, threaded=False)


if __name__ == "__main__":
    main()
