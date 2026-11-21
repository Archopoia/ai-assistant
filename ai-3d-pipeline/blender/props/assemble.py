"""
Step 05 — load all parts, check gaps, export FBX+GLB, render views.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import frame_objects, render_view  # noqa: E402
from blender.common.utils import (  # noqa: E402
    clear_scene,
    log,
    pipeline_args,
    triangle_count,
    write_json,
)


def import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def gap_between(a: bpy.types.Object, b: bpy.types.Object) -> float:
    """Approximate minimum distance between bounding boxes (0 if overlapping/touching)."""
    aw = [a.matrix_world @ Vector(c) for c in a.bound_box]
    bw = [b.matrix_world @ Vector(c) for c in b.bound_box]
    a_min = Vector((min(v.x for v in aw), min(v.y for v in aw), min(v.z for v in aw)))
    a_max = Vector((max(v.x for v in aw), max(v.y for v in aw), max(v.z for v in aw)))
    b_min = Vector((min(v.x for v in bw), min(v.y for v in bw), min(v.z for v in bw)))
    b_max = Vector((max(v.x for v in bw), max(v.y for v in bw), max(v.z for v in bw)))
    dx = max(0.0, max(a_min.x - b_max.x, b_min.x - a_max.x))
    dy = max(0.0, max(a_min.y - b_max.y, b_min.y - a_max.y))
    dz = max(0.0, max(a_min.z - b_max.z, b_min.z - a_max.z))
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def main() -> None:
    args = pipeline_args()
    asset = args["asset"]
    base = ROOT / "examples" / "props" / asset
    parts_doc = json.loads((base / "parts.json").read_text())
    clear_scene()

    objects: dict[str, bpy.types.Object] = {}
    for part in parts_doc["parts"]:
        glb = base / "parts" / f"{part['name']}.glb"
        if not glb.exists():
            raise FileNotFoundError(glb)
        imported = import_glb(glb)
        if not imported:
            raise RuntimeError(f"no mesh in {glb}")
        obj = imported[0]
        obj.name = part["name"]
        objects[part["name"]] = obj

    gaps = []
    for part in parts_doc["parts"]:
        parent = part.get("attaches_to")
        if not parent:
            continue
        g = gap_between(objects[part["name"]], objects[parent])
        gaps.append({"part": part["name"], "parent": parent, "gap_m": round(g, 5)})
        log(f"gap {part['name']} → {parent}: {g*100:.2f} cm")

    total_tris = sum(triangle_count(o) for o in objects.values())
    # join for export
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(objects.values()))
    if len(objects) > 1:
        bpy.ops.object.join()
    final = bpy.context.active_object
    final.name = asset

    bbox = [final.matrix_world @ Vector(c) for c in final.bound_box]
    size = {
        "x": round(max(v.x for v in bbox) - min(v.x for v in bbox), 4),
        "y": round(max(v.y for v in bbox) - min(v.y for v in bbox), 4),
        "z": round(max(v.z for v in bbox) - min(v.z for v in bbox), 4),
    }

    exports = base / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    glb = exports / f"{asset}.glb"
    fbx = exports / f"{asset}.fbx"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB")
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=False, apply_scale_options="FBX_SCALE_ALL")

    scale = frame_objects([final])
    for view in ("front", "side", "three_quarter"):
        render_view(base / "renders" / f"assemble_{view}.png", view, px=768, ortho_scale=scale)

    report = {
        "asset": asset,
        "triangles": total_tris,
        "budget": parts_doc.get("triangle_budget", 2000),
        "over_budget": total_tris > parts_doc.get("triangle_budget", 2000),
        "bounding_size_m": size,
        "expected_size_m": parts_doc.get("bounding_size_m"),
        "gaps": gaps,
        "exports": [str(glb.relative_to(ROOT)), str(fbx.relative_to(ROOT))],
    }
    write_json(exports / "assemble_report.json", report)
    log(json.dumps(report, indent=2))
    if any(g["gap_m"] > 0.002 for g in gaps):
        log("WARNING: floating parts detected (>2 mm gap)")


if __name__ == "__main__":
    main()
