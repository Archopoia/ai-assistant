#!/usr/bin/env python3
"""Step 04 QC — compare part render to orthographic reference; return cm diffs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _sil(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    return mask


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) < 5:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def compare(
    render: Path,
    reference: Path,
    *,
    expected_height_m: float,
    expected_width_m: float | None = None,
) -> dict:
    """
    Scale using reference silhouette height → metres.
    Returns size deltas in centimetres and a 0..1 match score.
    """
    a = _sil(reference)
    b = cv2.resize(_sil(render), (a.shape[1], a.shape[0]))
    ba, bb = _bbox(a), _bbox(b)
    if not ba or not bb:
        return {"ok": False, "score": 0.0, "diff_cm": {}, "note": "empty silhouette"}

    ax0, ay0, ax1, ay1 = ba
    bx0, by0, bx1, by1 = bb
    ref_h_px = max(1, ay1 - ay0)
    ren_h_px = max(1, by1 - by0)
    ref_w_px = max(1, ax1 - ax0)
    ren_w_px = max(1, bx1 - bx0)

    m_per_px = expected_height_m / ref_h_px
    height_err_m = (ren_h_px - ref_h_px) * m_per_px
    width_err_m = (ren_w_px - ref_w_px) * m_per_px

    inter = np.logical_and(a > 0, b > 0).sum()
    union = np.logical_or(a > 0, b > 0).sum()
    iou = float(inter / union) if union else 0.0

    # side-by-side PNG for human/guide QC
    ref_img = cv2.imread(str(reference))
    ren_img = cv2.imread(str(render))
    ren_img = cv2.resize(ren_img, (ref_img.shape[1], ref_img.shape[0]))
    combo = np.concatenate([ref_img, ren_img], axis=1)

    scale_h = ref_h_px / ren_h_px
    scale_w = ref_w_px / ren_w_px
    # Guide: stop when silhouette matches well enough (cm drift listed for the report)
    ok = iou >= 0.55 and abs(height_err_m) < 0.04 and abs(width_err_m) < 0.05

    return {
        "ok": ok,
        "score": round(iou, 4),
        "diff_cm": {
            "height": round(height_err_m * 100, 2),
            "width": round(width_err_m * 100, 2),
        },
        "scale_hint": {"height": round(scale_h, 4), "width": round(scale_w, 4)},
        "expected_height_m": expected_height_m,
        "expected_width_m": expected_width_m,
        "combo_bgr": combo,  # caller may save
    }


def save_combo(result: dict, out: Path) -> None:
    if "combo_bgr" in result and result["combo_bgr"] is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), result["combo_bgr"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", type=Path, required=True)
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--height-m", type=float, required=True)
    ap.add_argument("--width-m", type=float, default=None)
    ap.add_argument("--combo", type=Path, default=None)
    args = ap.parse_args()
    r = compare(args.render, args.ref, expected_height_m=args.height_m, expected_width_m=args.width_m)
    if args.combo:
        save_combo(r, args.combo)
    out = {k: v for k, v in r.items() if k != "combo_bgr"}
    print(json.dumps(out, indent=2))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
