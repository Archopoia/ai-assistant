"""
Step 04 — build one prop part from parts.json using bmesh.
Supports box parts and contour extrusion from measured side silhouette.

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


def _apply_color(obj: bpy.types.Object, part: dict) -> None:
    color = part.get("color", [0.55, 0.4, 0.25, 1.0])
    if len(color) == 3:
        color = list(color) + [1.0]
    mat = flat_material(f"mat_{part['name']}", tuple(color))
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def _bevel(obj: bpy.types.Object, part: dict) -> None:
    bevel_m = float(part.get("bevel_m", 0.002))
    if bevel_m <= 0:
        return
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = bevel_m
    mod.segments = int(part.get("bevel_segments", 1))
    mod.limit_method = "ANGLE"
    apply_all_modifiers(obj)


def box_from_part(part: dict) -> bpy.types.Object:
    sx = float(part["width"])
    sy = float(part["depth"])
    sz = float(part["height"])
    y0 = float(part.get("y_start", 0.0))
    y1 = float(part.get("y_end", sy))
    depth = abs(y1 - y0) if "y_start" in part else sy
    cx = float(part.get("x", 0.0))
    cz = float(part.get("z", sz / 2))
    cy = -(y0 + depth / 2)

    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = part["name"]
    obj.scale = (sx, depth, sz)
    bpy.ops.object.transform_apply(scale=True)
    obj.location = (cx, cy, cz)
    _bevel(obj, part)
    _apply_color(obj, part)
    return obj


def contour_from_part(part: dict, side_ref: Path | None) -> bpy.types.Object:
    """
    Tutorial step 04: threshold side view → contour (~30 pts) → extrude to width → bevel.
    Contour points may be embedded in parts.json (pixel coords) or read from side_ref.
    """
    width = float(part["width"])
    depth = float(part["depth"])
    height = float(part["height"])
    pts = part.get("contour_side") or []

    if (not pts) and side_ref and side_ref.exists():
        # fallback: load via numpy-free approximate — use image as plane not ideal;
        # expect measure_parts to embed contour
        return box_from_part(part)

    if len(pts) < 3:
        return box_from_part(part)

    # normalize pixel contour to metres in XZ (side view: x→depth/Y, y→height/Z)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)

    bm = bmesh.new()
    verts = []
    for x, y in pts:
        # image y down → z up; x → local Y (depth)
        ly = ((x - min_x) / span_x - 0.5) * depth
        lz = (1.0 - (y - min_y) / span_y) * height
        verts.append(bm.verts.new((0.0, ly, lz)))
    bm.verts.ensure_lookup_table()
    for i in range(len(verts)):
        bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))
    # fill face
    try:
        bm.faces.new(verts)
    except ValueError:
        # non-planar / twisted — fall back
        bm.free()
        return box_from_part(part)

    mesh = bpy.data.meshes.new(part["name"] + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(part["name"], mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # extrude along X (width)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value": (width, 0, 0)}
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    # center on X
    obj.location.x = float(part.get("x", 0.0)) - width / 2
    obj.location.y = float(part.get("y_start", 0.0)) * 0.0  # already centered in Y
    # shift so base sits correctly — z already from contour
    cy = -depth / 2
    obj.location.y += cy

    _bevel(obj, part)
    _apply_color(obj, part)
    return obj


def main() -> None:
    args = pipeline_args()
    asset = args["asset"]
    part_name = args["part"]
    base = ROOT / "examples" / "props" / asset
    parts_path = base / "parts.json"
    parts = json.loads(parts_path.read_text(encoding="utf-8"))
    part = next(p for p in parts["parts"] if p["name"] == part_name)

    clear_scene()
    side_ref = base / "references" / "side.png"
    build = part.get("build", "box")
    if build == "contour":
        obj = contour_from_part(part, side_ref if side_ref.exists() else None)
        log(f"contour build for {part_name}")
    else:
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

    # optional side-by-side note if reference exists
    meta = {
        "part": part_name,
        "build": build,
        "triangles": triangle_count(obj),
        "location": list(obj.location),
        "dimensions": list(obj.dimensions),
        "render": str(render.relative_to(ROOT)),
        "has_side_ref": side_ref.exists(),
    }
    write_json(base / "parts" / f"{part_name}_meta.json", meta)
    log(f"built {part_name}: {meta['triangles']} tris → {out_glb}")


if __name__ == "__main__":
    main()
