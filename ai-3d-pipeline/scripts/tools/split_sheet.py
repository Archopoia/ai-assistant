#!/usr/bin/env python3
"""
Split a concept / turnaround sheet into separate orthographic views.

Detects vertical or horizontal gutters; falls back to equal 3-panel split.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _panel_bounds(gray: np.ndarray, axis: int, min_gap_frac: float = 0.02) -> list[tuple[int, int]]:
    """Find content panels separated by low-ink gutters along axis (0=rows, 1=cols)."""
    # ink = non-white-ish
    ink = gray < 245
    proj = ink.mean(axis=axis)
    thresh = max(0.02, float(proj.mean()) * 0.35)
    active = proj > thresh
    # smooth
    k = max(3, len(proj) // 80)
    kernel = np.ones(k) / k
    smooth = np.convolve(active.astype(np.float32), kernel, mode="same") > 0.5

    gaps = []
    in_gap = False
    start = 0
    for i, v in enumerate(smooth):
        if not v and not in_gap:
            in_gap = True
            start = i
        elif v and in_gap:
            in_gap = False
            if (i - start) >= max(4, int(len(proj) * min_gap_frac)):
                gaps.append((start, i))
    if in_gap and (len(smooth) - start) >= max(4, int(len(proj) * min_gap_frac)):
        gaps.append((start, len(smooth)))

    # panels = between gaps
    cuts = [0] + [ (a + b) // 2 for a, b in gaps ] + [len(proj)]
    panels = []
    for a, b in zip(cuts, cuts[1:]):
        if b - a > len(proj) * 0.08:
            panels.append((a, b))
    return panels


def split_image(path: Path, n_hint: int = 3) -> list[np.ndarray]:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        # composite on white
        a = img[:, :, 3:4].astype(np.float32) / 255.0
        rgb = img[:, :, :3].astype(np.float32)
        bgr = (rgb * a + 255 * (1 - a)).astype(np.uint8)
    else:
        bgr = img
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # mean(axis=0) length=width → column gutters; axis=1 → row gutters
    col_panels = _panel_bounds(gray, axis=0)
    row_panels = _panel_bounds(gray, axis=1)

    use_cols = len(col_panels) >= 2 and (len(col_panels) >= len(row_panels))
    panels = col_panels if use_cols else row_panels
    if len(panels) < 2:
        # equal split
        panels = []
        if w >= h:
            step = w // n_hint
            for i in range(n_hint):
                panels.append((i * step, w if i == n_hint - 1 else (i + 1) * step))
            use_cols = True
        else:
            step = h // n_hint
            for i in range(n_hint):
                panels.append((i * step, h if i == n_hint - 1 else (i + 1) * step))
            use_cols = False

    crops = []
    for a, b in panels[: max(n_hint, len(panels))]:
        if use_cols:
            crop = bgr[:, a:b]
        else:
            crop = bgr[a:b, :]
        # trim empty margins
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ys, xs = np.where(g < 250)
        if len(xs) > 10:
            x0, x1 = max(0, xs.min() - 4), min(crop.shape[1], xs.max() + 4)
            y0, y1 = max(0, ys.min() - 4), min(crop.shape[0], ys.max() + 4)
            crop = crop[y0:y1, x0:x1]
        crops.append(crop)
    return crops


def save_character_views(sheet: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    crops = split_image(sheet, n_hint=3)
    names = ["view_front.png", "view_right.png", "view_back.png"]
    # If 4 panels: front, left, back, right — map article order
    if len(crops) >= 4:
        mapping = [
            ("view_front.png", crops[0]),
            ("view_right.png", crops[3]),
            ("view_back.png", crops[2]),
        ]
    else:
        while len(crops) < 3:
            crops.append(crops[-1])
        mapping = list(zip(names, crops[:3]))
    saved = {}
    for name, crop in mapping:
        path = out_dir / name
        cv2.imwrite(str(path), crop)
        saved[name] = str(path)
    return saved


def save_prop_views(sheet: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    crops = split_image(sheet, n_hint=3)
    names = ["front.png", "side.png", "top.png"]
    while len(crops) < 3:
        crops.append(crops[-1])
    saved = {}
    for name, crop in zip(names, crops[:3]):
        path = out_dir / name
        cv2.imwrite(str(path), crop)
        saved[name] = str(path)
    return saved


def main() -> int:
    ap = argparse.ArgumentParser(description="Split turnaround / reference sheet into views")
    ap.add_argument("sheet", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--kind", choices=("character", "prop"), default="character")
    args = ap.parse_args()
    saved = save_character_views(args.sheet, args.out) if args.kind == "character" else save_prop_views(args.sheet, args.out)
    print(json.dumps({"saved": saved}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
