"""
Step 04 — build one prop part from parts.json using bmesh.
Run: blender -b --python blender/props/build_part.py
PIPELINE_ARGS: {"asset":"crate","part":"body"}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import frame_objects, render_view  # noqa: E402
from blender.common.utils import (  # noqa: E402
    apply_all_modifiers,
    clear_scene,
    flat_material,
    log,
    pipeline_args,
    set_origin_base_center,
    triangle_count,
    write_json,
)


def box_from_part(part: dict) -> bpy.types.Object:
    """Create a beveled box for a measured part (metres)."""
    sx = float(part["width"])
    sy = float(part["depth"])
    sz = float(part["height"])
    # start/end along length (Y, forward -Y) from back end in metres
    y0 = float(part.get("y_start", 0.0))
    y1 = float(part.get("y_end", sy))
    depth = abs(y1 - y0) if "y_start" in part else sy
    cx = float(part.get("x", 0.0))
    cz = float(part.get("z", sz / 2))
    cy = -(y0 + depth / 2)  # forward is -Y; back end at y=0 in part space → world -Y

    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = part["name"]
    obj.scale = (sx, depth, sz)
    bpy.ops.object.transform_apply(scale=True)
    obj.location = (cx, cy, cz)

    bevel_m = float(part.get("bevel_m", 0.002))
    if bevel_m > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel_m
        mod.segments = int(part.get("bevel_segments", 1))
        mod.limit_method = "ANGLE"
        apply_all_modifiers(obj)

    color = part.get("color", [0.55, 0.4, 0.25, 1.0])
    if len(color) == 3:
        color = list(color) + [1.0]
    mat = flat_material(f"mat_{part['name']}", tuple(color))
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


def main() -> None:
    args = pipeline_args()
    asset = args["asset"]
    part_name = args["part"]
    base = ROOT / "examples" / "props" / asset
    parts_path = base / "parts.json"
    parts = json.loads(parts_path.read_text())
    part = next(p for p in parts["parts"] if p["name"] == part_name)

    clear_scene()
    obj = box_from_part(part)
    set_origin_base_center(obj)

    out_blend = base / "parts" / f"{part_name}.blend"
    out_glb = base / "parts" / f"{part_name}.glb"
    out_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_selection=False)

    scale = frame_objects([obj])
    render = base / "renders" / f"{part_name}_side.png"
    render_view(render, "side", px=int(args.get("render_px", 768)), ortho_scale=scale)

    meta = {
        "part": part_name,
        "triangles": triangle_count(obj),
        "location": list(obj.location),
        "dimensions": list(obj.dimensions),
        "render": str(render.relative_to(ROOT)),
    }
    write_json(base / "parts" / f"{part_name}_meta.json", meta)
    log(f"built {part_name}: {meta['triangles']} tris → {out_glb}")


if __name__ == "__main__":
    main()
