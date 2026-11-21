#!/usr/bin/env python3
"""Step 03 — measure orthographic front/side refs → parts.json (OpenCV, free)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _silhouette(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def _contour_poly(mask: np.ndarray, max_pts: int = 30) -> list[list[float]]:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return []
    c = max(cnts, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    eps = max(peri * 0.012, 1.0)
    approx = cv2.approxPolyDP(c, eps, True)
    guard = 0
    while len(approx) > max_pts and guard < 8:
        eps *= 1.4
        approx = cv2.approxPolyDP(c, eps, True)
        guard += 1
    return approx.reshape(-1, 2).astype(float).tolist()


def _bands(mask: np.ndarray, n_max: int = 5) -> list[tuple[float, float]]:
    h, _ = mask.shape
    row = (mask > 0).mean(axis=1)
    active = row > 0.02
    bands, in_band, start = [], False, 0
    for i, v in enumerate(active):
        if v and not in_band:
            in_band, start = True, i
        elif not v and in_band:
            in_band = False
            if i - start > h * 0.04:
                bands.append((start, i))
    if in_band and h - start > h * 0.04:
        bands.append((start, h))
    merged = []
    for b in bands:
        if merged and b[0] - merged[-1][1] < h * 0.03:
            merged[-1] = (merged[-1][0], b[1])
        else:
            merged.append(b)
    out = []
    for y0, y1 in merged[:n_max]:
        out.append((max(0.0, 1.0 - y1 / h), min(1.0, 1.0 - y0 / h)))
    out.sort()
    return out or [(0.0, 1.0)]


def _width_frac(mask: np.ndarray, z0: float, z1: float) -> float:
    h, w = mask.shape
    y1 = int((1.0 - z0) * h)
    y0 = int((1.0 - z1) * h)
    y0, y1 = max(0, min(y0, y1)), min(h, max(y0, y1))
    strip = mask[y0:y1, :]
    if strip.size == 0:
        return 0.7
    xs = np.where((strip > 0).mean(axis=0) > 0.05)[0]
    if len(xs) < 2:
        return 0.7
    return float((xs.max() - xs.min()) / w)


def measure(
    *,
    front: Path | None,
    side: Path | None,
    name: str,
    width_m: float = 0.6,
    depth_m: float = 0.6,
    height_m: float = 0.5,
) -> dict:
    side_path = side if side and side.exists() else front
    if side_path is None or not Path(side_path).exists():
        raise FileNotFoundError("Need side.png or front.png")
    side_mask = _silhouette(Path(side_path))
    front_mask = _silhouette(front) if front and Path(front).exists() else None
    bands = _bands(side_mask)
    contour = _contour_poly(side_mask)

    colors = [
        [0.55, 0.38, 0.22],
        [0.45, 0.32, 0.18],
        [0.35, 0.35, 0.38],
        [0.5, 0.4, 0.3],
        [0.4, 0.28, 0.16],
    ]
    names = ["body", "lid", "band", "detail_a", "detail_b"]
    parts = []
    for i, (z0, z1) in enumerate(bands):
        part_h = max(0.01, (z1 - z0) * height_m)
        z_mid = (z0 + z1) * 0.5 * height_m
        w_frac = _width_frac(side_mask, z0, z1)
        if front_mask is not None:
            w_frac = max(w_frac, _width_frac(front_mask, z0, z1))
        part_w = max(0.02, width_m * (0.55 + 0.45 * w_frac))
        part_d = max(0.02, depth_m * (0.55 + 0.45 * w_frac))
        pname = names[i] if i < len(names) else f"part_{i+1}"
        parts.append(
            {
                "name": pname,
                "width": round(part_w, 4),
                "depth": round(part_d, 4),
                "height": round(part_h, 4),
                "y_start": 0.0,
                "y_end": round(part_d, 4),
                "x": 0.0,
                "z": round(z_mid, 4),
                "color": colors[i % len(colors)],
                "attaches_to": None if i == 0 else "body",
                "bevel_m": 0.002,
                "build": "box",
            }
        )

    if parts and contour:
        # assign contour to tallest band
        idx = max(range(len(parts)), key=lambda i: parts[i]["height"])
        parts[idx]["build"] = "contour"
        parts[idx]["contour_side"] = contour

    return {
        "name": name,
        "units": "meters",
        "triangle_budget": 2000,
        "bounding_size_m": {"x": width_m, "y": depth_m, "z": height_m},
        "notes": f"Measured from orthographic refs ({Path(side_path).name}) via OpenCV.",
        "parts": parts,
        "source_refs": {
            "side": str(side_path),
            "front": str(front) if front else None,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", type=Path)
    ap.add_argument("--side", type=Path)
    ap.add_argument("--name", default="prop")
    ap.add_argument("--width", type=float, default=0.6)
    ap.add_argument("--depth", type=float, default=0.6)
    ap.add_argument("--height", type=float, default=0.5)
    ap.add_argument("-o", type=Path, required=True)
    args = ap.parse_args()
    doc = measure(
        front=args.front,
        side=args.side,
        name=args.name,
        width_m=args.width,
        depth_m=args.depth,
        height_m=args.height,
    )
    args.o.parent.mkdir(parents=True, exist_ok=True)
    args.o.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {args.o} ({len(doc['parts'])} parts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
