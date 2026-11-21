"""
Step 08 — clean generator GLB: orient, feet on floor, merge, normals, decimate+bake, crowd LOD.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Euler

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


def get_mesh() -> bpy.types.Object:
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh after import")
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
    return bpy.context.active_object


def orient_and_scale(obj: bpy.types.Object, height_m: float) -> None:
    # Tripo often faces +X; rotate to -Y forward
    obj.rotation_euler = Euler((0, 0, -math.pi / 2), "XYZ")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(v.z for v in bbox)
    obj.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cur_h = max(v.z for v in bbox) - min(v.z for v in bbox)
    if cur_h > 1e-6:
        s = height_m / cur_h
        obj.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # center XY
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cx = (min(v.x for v in bbox) + max(v.x for v in bbox)) / 2
    cy = (min(v.y for v in bbox) + max(v.y for v in bbox)) / 2
    obj.location.x -= cx
    obj.location.y -= cy
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def merge_and_normals(obj: bpy.types.Object) -> dict:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # loose parts
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_loose()
    bpy.ops.object.mode_set(mode="OBJECT")
    loose = sum(1 for v in obj.data.vertices if v.select)
    return {"loose_verts": loose, "triangles": triangle_count(obj)}


def decimate_copy(obj: bpy.types.Object, budget: int, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()
    low = bpy.context.active_object
    low.name = name
    tris = max(triangle_count(low), 1)
    ratio = min(1.0, budget / tris)
    mod = low.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return low


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    src = Path(args.get("input", base / "exports" / "raw.glb"))
    height = float(args.get("height_m", 1.15))
    hero_budget = int(args.get("hero_triangles", 40000))
    crowd_budget = int(args.get("crowd_triangles", 3000))

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(src))
    obj = get_mesh()
    obj.name = name
    orient_and_scale(obj, height)
    stats = merge_and_normals(obj)

    hero = decimate_copy(obj, hero_budget, f"{name}_hero")
    crowd = decimate_copy(obj, crowd_budget, f"{name}_crowd")

    # hide original heavy if different
    if obj.name != hero.name:
        obj.hide_render = True
        obj.hide_viewport = True

    exports = base / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    hero.select_set(True)
    bpy.context.view_layer.objects.active = hero
    bpy.ops.export_scene.gltf(filepath=str(exports / f"{name}_clean.glb"), export_format="GLB", use_selection=True)
    bpy.ops.object.select_all(action="DESELECT")
    crowd.select_set(True)
    bpy.context.view_layer.objects.active = crowd
    bpy.ops.export_scene.gltf(filepath=str(exports / f"{name}_crowd.glb"), export_format="GLB", use_selection=True)

    # QC renders of hero
    crowd.hide_render = True
    crowd.hide_viewport = True
    hero.hide_render = False
    hero.hide_viewport = False
    scale = frame_objects([hero])
    for view in ("front", "side", "back"):
        render_view(base / "renders" / f"clean_{view}.png", view, px=768, ortho_scale=scale)

    report = {
        **stats,
        "hero_triangles": triangle_count(hero),
        "crowd_triangles": triangle_count(crowd),
        "height_m": height,
    }
    write_json(exports / "clean_report.json", report)
    log(json.dumps(report))


if __name__ == "__main__":
    import json

    main()
