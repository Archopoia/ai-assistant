"""
Step 09 — tag faces into body parts by position (+ optional colour heuristics).
Stores vertex groups for later weight rules.
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
from blender.common.utils import clear_scene, flat_material, log, pipeline_args, write_json  # noqa: E402

PART_COLORS = {
    "head": (0.95, 0.8, 0.7, 1),
    "torso": (0.3, 0.45, 0.7, 1),
    "arm_L": (0.9, 0.5, 0.3, 1),
    "arm_R": (0.9, 0.35, 0.35, 1),
    "hand_L": (0.95, 0.85, 0.6, 1),
    "hand_R": (0.95, 0.75, 0.5, 1),
    "leg_L": (0.35, 0.6, 0.35, 1),
    "leg_R": (0.25, 0.5, 0.3, 1),
    "coat": (0.15, 0.15, 0.2, 1),
}


def classify(co: Vector, height: float) -> str:
    z = co.z / max(height, 1e-6)
    x = co.x
    if z > 0.82:
        return "head"
    if z > 0.55:
        if x < -0.12 * height:
            return "arm_L" if z > 0.62 else "hand_L"
        if x > 0.12 * height:
            return "arm_R" if z > 0.62 else "hand_R"
        return "torso"
    if z > 0.35:
        if abs(x) > 0.14 * height:
            return "coat"
        return "torso" if z > 0.45 else ("leg_L" if x < 0 else "leg_R")
    return "leg_L" if x < 0 else "leg_R"


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    src = base / "exports" / f"{name}_clean.glb"
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(src))
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    obj.name = name

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    height = max(v.z for v in bbox) - min(v.z for v in bbox)

    # vertex groups
    for pname in PART_COLORS:
        if pname not in obj.vertex_groups:
            obj.vertex_groups.new(name=pname)

    mesh = obj.data
    counts = {k: 0 for k in PART_COLORS}
    for v in mesh.vertices:
        world = obj.matrix_world @ v.co
        part = classify(world, height)
        for gref in list(v.groups):
            obj.vertex_groups[gref.group].remove([v.index])
        obj.vertex_groups[part].add([v.index], 1.0, "REPLACE")
        counts[part] += 1

    # visual materials per part via geometry nodes? simpler: vertex paint style — assign materials by face majority
    mesh.materials.clear()
    mat_index = {}
    for i, (pname, col) in enumerate(PART_COLORS.items()):
        mat = flat_material(f"part_{pname}", col)
        mesh.materials.append(mat)
        mat_index[pname] = i

    group_index = {g.index: g.name for g in obj.vertex_groups}
    for poly in mesh.polygons:
        tally = {k: 0 for k in PART_COLORS}
        for vi in poly.vertices:
            for gref in mesh.vertices[vi].groups:
                name = group_index.get(gref.group)
                if name in tally and gref.weight > 0.5:
                    tally[name] += 1
        part = max(tally, key=tally.get)
        poly.material_index = mat_index[part]

    out = base / "exports" / f"{name}_parts.glb"
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB")
    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_parts.blend"))

    scale = frame_objects([obj])
    for view in ("front", "back"):
        render_view(base / "renders" / f"parts_{view}.png", view, px=768, ortho_scale=scale)

    write_json(base / "exports" / "parts_report.json", {"counts": counts, "height_m": height})
    log(json.dumps(counts))


if __name__ == "__main__":
    main()
