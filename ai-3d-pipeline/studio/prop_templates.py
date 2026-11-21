"""Build parts.json for common hard-surface props (tutorial step 03)."""
from __future__ import annotations

from typing import Any


def _crate(w: float, d: float, h: float, wood=(0.55, 0.38, 0.22), metal=(0.35, 0.35, 0.38)) -> list[dict]:
    lid_h = min(0.05, h * 0.1)
    body_h = h - lid_h
    band_h = min(0.04, body_h * 0.12)
    return [
        {
            "name": "body",
            "width": w,
            "depth": d,
            "height": body_h,
            "y_start": 0.0,
            "y_end": d,
            "x": 0.0,
            "z": body_h / 2,
            "color": list(wood),
            "attaches_to": None,
            "bevel_m": 0.002,
        },
        {
            "name": "lid",
            "width": w + 0.02,
            "depth": d + 0.02,
            "height": lid_h,
            "y_start": 0.0,
            "y_end": d + 0.02,
            "x": 0.0,
            "z": body_h + lid_h / 2,
            "color": [max(0.0, c - 0.07) for c in wood],
            "attaches_to": "body",
            "bevel_m": 0.002,
        },
        {
            "name": "band",
            "width": w + 0.02,
            "depth": d + 0.02,
            "height": band_h,
            "y_start": 0.0,
            "y_end": d + 0.02,
            "x": 0.0,
            "z": body_h * 0.5,
            "color": list(metal),
            "attaches_to": "body",
            "bevel_m": 0.001,
        },
    ]


def _box(w: float, d: float, h: float, color=(0.5, 0.45, 0.4)) -> list[dict]:
    return [
        {
            "name": "body",
            "width": w,
            "depth": d,
            "height": h,
            "y_start": 0.0,
            "y_end": d,
            "x": 0.0,
            "z": h / 2,
            "color": list(color),
            "attaches_to": None,
            "bevel_m": 0.002,
        }
    ]


def _barrel(diameter: float, h: float) -> list[dict]:
    # Approximate barrel with stacked beveled boxes (hard-surface path from tutorial)
    r = diameter
    hoop = min(0.03, h * 0.08)
    return [
        {
            "name": "body",
            "width": r,
            "depth": r,
            "height": h - 2 * hoop,
            "y_start": 0.0,
            "y_end": r,
            "x": 0.0,
            "z": h / 2,
            "color": [0.42, 0.28, 0.16],
            "attaches_to": None,
            "bevel_m": 0.01,
        },
        {
            "name": "hoop_bottom",
            "width": r + 0.02,
            "depth": r + 0.02,
            "height": hoop,
            "y_start": 0.0,
            "y_end": r + 0.02,
            "x": 0.0,
            "z": hoop / 2,
            "color": [0.3, 0.3, 0.32],
            "attaches_to": "body",
            "bevel_m": 0.001,
        },
        {
            "name": "hoop_top",
            "width": r + 0.02,
            "depth": r + 0.02,
            "height": hoop,
            "y_start": 0.0,
            "y_end": r + 0.02,
            "x": 0.0,
            "z": h - hoop / 2,
            "color": [0.3, 0.3, 0.32],
            "attaches_to": "body",
            "bevel_m": 0.001,
        },
    ]


def _table(w: float, d: float, h: float) -> list[dict]:
    top_h = min(0.04, h * 0.08)
    leg = min(0.06, w * 0.08)
    leg_h = h - top_h
    parts = [
        {
            "name": "top",
            "width": w,
            "depth": d,
            "height": top_h,
            "y_start": 0.0,
            "y_end": d,
            "x": 0.0,
            "z": h - top_h / 2,
            "color": [0.5, 0.35, 0.2],
            "attaches_to": None,
            "bevel_m": 0.002,
        }
    ]
    offsets = [
        ("leg_fl", -w / 2 + leg, -d / 2 + leg),
        ("leg_fr", w / 2 - leg, -d / 2 + leg),
        ("leg_bl", -w / 2 + leg, d / 2 - leg),
        ("leg_br", w / 2 - leg, d / 2 - leg),
    ]
    for name, x, y in offsets:
        parts.append(
            {
                "name": name,
                "width": leg,
                "depth": leg,
                "height": leg_h,
                "y_start": y - leg / 2 + d / 2,
                "y_end": y + leg / 2 + d / 2,
                "x": x,
                "z": leg_h / 2,
                "color": [0.4, 0.28, 0.16],
                "attaches_to": "top",
                "bevel_m": 0.001,
            }
        )
    return parts


TEMPLATES = {
    "crate": lambda w, d, h: _crate(w, d, h),
    "box": lambda w, d, h: _box(w, d, h),
    "chest": lambda w, d, h: _crate(w, d, h, wood=(0.45, 0.25, 0.12), metal=(0.55, 0.45, 0.2)),
    "barrel": lambda w, d, h: _barrel(max(w, d), h),
    "table": lambda w, d, h: _table(w, d, h),
    "block": lambda w, d, h: _box(w, d, h, color=(0.55, 0.55, 0.55)),
}


def suggest_parts(
    *,
    name: str,
    kind: str = "crate",
    width_m: float = 0.6,
    depth_m: float = 0.6,
    height_m: float = 0.5,
    notes: str = "",
) -> dict[str, Any]:
    kind = (kind or "crate").lower().strip()
    if kind not in TEMPLATES:
        # fuzzy from free text
        blob = f"{kind} {name} {notes}".lower()
        if "barrel" in blob or "drum" in blob:
            kind = "barrel"
        elif "table" in blob or "desk" in blob:
            kind = "table"
        elif "chest" in blob or "trunk" in blob:
            kind = "chest"
        elif "block" in blob or "stone" in blob or "cube" in blob:
            kind = "block"
        elif "box" in blob:
            kind = "box"
        else:
            kind = "crate"

    parts = TEMPLATES[kind](width_m, depth_m, height_m)
    return {
        "name": name,
        "units": "meters",
        "triangle_budget": 2000,
        "kind": kind,
        "bounding_size_m": {"x": width_m, "y": depth_m, "z": height_m},
        "notes": notes
        or f"Suggested {kind} from Studio. Edit parts then build (tutorial steps 03–05).",
        "parts": parts,
    }
