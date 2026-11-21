"""Turn a free-text prompt into a route + prop measurements (tutorial step 01)."""
from __future__ import annotations

import re
from typing import Any


def _meters_from_text(text: str) -> tuple[float | None, float | None, float | None]:
    """Parse sizes like 60cm, 0.6m, 2 ft."""
    t = text.lower().replace(",", ".")
    found: list[float] = []
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(cm|mm|m|meters?|metres?|ft|feet|in|inches)?",
        t,
    ):
        val = float(m.group(1))
        unit = (m.group(2) or "m").lower()
        if unit in ("mm",):
            val /= 1000.0
        elif unit in ("cm",):
            val /= 100.0
        elif unit in ("ft", "feet"):
            val *= 0.3048
        elif unit in ("in", "inches"):
            val *= 0.0254
        # bare numbers near size words only — skip years etc.
        if unit or "x" in t[max(0, m.start() - 3) : m.end() + 3]:
            if 0.01 <= val <= 20:
                found.append(val)
    w = d = h = None
    if len(found) >= 3:
        w, d, h = found[0], found[1], found[2]
    elif len(found) == 2:
        w, h = found[0], found[1]
        d = found[0]
    elif len(found) == 1:
        w = d = h = found[0]
    return w, d, h


_PROP_HINTS = (
    "barrel", "crate", "box", "chest", "table", "chair", "prop", "weapon",
    "sword", "rifle", "furniture", "rock", "stone", "pillar", "door", "wagon",
)
_CHAR_HINTS = (
    "character", "creature", "hero", "npc", "person", "girl", "boy", "man",
    "woman", "animal", "monster", "robot", "humanoid", "t-pose", "tpose",
    "a-pose", "apose", "turnaround", "warrior", "hunter", "portrait",
)
_BUILD_HINTS = ("building", "house", "shop", "tower", "city", "street", "block")


def detect_route(prompt: str, route: str = "auto", *, has_image: bool = False) -> str:
    if route and route != "auto":
        return route
    t = (prompt or "").lower().strip()
    if any(k in t for k in _BUILD_HINTS):
        return "buildings"
    if any(k in t for k in _CHAR_HINTS):
        return "character"
    if any(k in t for k in _PROP_HINTS):
        return "prop"
    # Picture-only / generic "asset from picture" → character (guide path)
    if has_image and (not t or t in {"asset from picture", "asset", "from picture", "image"}):
        return "character"
    if has_image and not any(k in t for k in _PROP_HINTS):
        return "character"
    return "prop"


def asset_name_from_prompt(prompt: str, fallback: str = "asset", filename: str | None = None) -> str:
    # Prefer uploaded filename over generic placeholder prompts
    if filename:
        stem = Pathish(filename)
        if stem and stem not in {"image", "file", "upload", "blob", "asset_from_picture"}:
            return stem
    t = (prompt or "").strip()
    if not t or t.lower() in {"asset from picture", "asset", "from picture"}:
        return fallback
    low = t.lower()
    head = re.split(r"\bfor\b|\.|,", low, maxsplit=1)[0].strip()
    m = re.search(r"(?:a|an|the)\s+([a-z0-9][\w\s-]{1,40})", head)
    if m:
        chunk = m.group(1)
    else:
        chunk = re.sub(r"^(make|create|build|generate)\s+", "", head).strip()
        chunk = chunk[:40]
    chunk = re.sub(r"[^a-z0-9]+", "_", chunk).strip("_")
    return chunk[:48] or fallback


def Pathish(filename: str) -> str:
    base = re.sub(r"\.[a-z0-9]+$", "", filename.split("/")[-1].split("\\")[-1], flags=re.I)
    base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()
    return base[:48]


def prop_kind_from_prompt(prompt: str) -> str:
    t = (prompt or "").lower()
    pairs = [
        ("barrel", "barrel"),
        ("drum", "barrel"),
        ("table", "table"),
        ("desk", "table"),
        ("chest", "chest"),
        ("trunk", "chest"),
        ("crate", "crate"),
        ("box", "box"),
        ("cube", "block"),
        ("stone", "block"),
        ("block", "block"),
        ("rifle", "box"),
        ("gun", "box"),
        ("weapon", "box"),
    ]
    for key, kind in pairs:
        if key in t:
            return kind
    return "crate"


def parse_brief(
    prompt: str,
    route: str = "auto",
    *,
    has_image: bool = False,
    filename: str | None = None,
) -> dict[str, Any]:
    route = detect_route(prompt, route, has_image=has_image)
    fallback = "character" if route == "character" else ("buildings" if route == "buildings" else "prop")
    name = asset_name_from_prompt(prompt, fallback, filename=filename)
    w, d, h = _meters_from_text(prompt)
    return {
        "route": route,
        "name": name,
        "prompt": prompt.strip(),
        "prop_kind": prop_kind_from_prompt(prompt),
        "width_m": w or 0.6,
        "depth_m": d or 0.6,
        "height_m": h or 0.5,
        "sheet_prompt": (
            "Orthographic side view of "
            f"[{prompt.strip() or 'object'}], exactly side-on, no perspective.\n"
            "Plain white background, flat colours, no shadows, no reflections.\n"
            "Same scale as the front and top views. Nothing cut off at the edges."
            if route == "prop"
            else "Character turnaround sheet: front, right side, back. Orthographic, same height,\n"
            "A-pose, arms away from the body, legs apart. Empty hands: no weapon, no lantern,\n"
            "no bag in hand. Light grey background, flat even light, no shadows.\n"
            f"Design: {prompt.strip() or 'match the uploaded reference character'}"
        ),
    }
