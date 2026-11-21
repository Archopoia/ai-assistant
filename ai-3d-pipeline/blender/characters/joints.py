"""
Step 10 — estimate Mixamo-style joints from mesh bounds; write joints.json + debug dots.
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


def add_dot(name: str, loc, color=(1, 0, 0, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.015, location=loc)
    obj = bpy.context.active_object
    obj.name = f"joint_{name}"
    mat = flat_material(f"dot_{name}", color)
    obj.data.materials.append(mat)
    return obj


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    src = base / "exports" / f"{name}_parts.blend"
    if src.exists():
        bpy.ops.wm.open_mainfile(filepath=str(src))
        # remove old dots
        for o in list(bpy.data.objects):
            if o.name.startswith("joint_"):
                bpy.data.objects.remove(o, do_unlink=True)
        obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("joint_"))
    else:
        clear_scene()
        bpy.ops.import_scene.gltf(filepath=str(base / "exports" / f"{name}_clean.glb"))
        obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_x, max_x = min(v.x for v in bbox), max(v.x for v in bbox)
    min_y, max_y = min(v.y for v in bbox), max(v.y for v in bbox)
    min_z, max_z = min(v.z for v in bbox), max(v.z for v in bbox)
    h = max_z - min_z
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    # Mixamo-ish resting A-pose joint estimates (metres)
    joints = {
        "Hips": [cx, cy, min_z + 0.52 * h],
        "Spine": [cx, cy, min_z + 0.60 * h],
        "Spine1": [cx, cy, min_z + 0.68 * h],
        "Spine2": [cx, cy, min_z + 0.74 * h],
        "Neck": [cx, cy, min_z + 0.82 * h],
        "Head": [cx, cy, min_z + 0.92 * h],
        "LeftShoulder": [cx - 0.08 * h, cy, min_z + 0.78 * h],
        "LeftArm": [cx - 0.18 * h, cy, min_z + 0.76 * h],
        "LeftForeArm": [cx - 0.32 * h, cy - 0.02 * h, min_z + 0.62 * h],
        "LeftHand": [cx - 0.42 * h, cy - 0.02 * h, min_z + 0.50 * h],
        "RightShoulder": [cx + 0.08 * h, cy, min_z + 0.78 * h],
        "RightArm": [cx + 0.18 * h, cy, min_z + 0.76 * h],
        "RightForeArm": [cx + 0.32 * h, cy - 0.02 * h, min_z + 0.62 * h],
        "RightHand": [cx + 0.42 * h, cy - 0.02 * h, min_z + 0.50 * h],
        "LeftUpLeg": [cx - 0.08 * h, cy, min_z + 0.52 * h],
        "LeftLeg": [cx - 0.09 * h, cy, min_z + 0.28 * h],
        "LeftFoot": [cx - 0.09 * h, cy - 0.05 * h, min_z + 0.04 * h],
        "LeftToeBase": [cx - 0.09 * h, cy - 0.12 * h, min_z + 0.02 * h],
        "RightUpLeg": [cx + 0.08 * h, cy, min_z + 0.52 * h],
        "RightLeg": [cx + 0.09 * h, cy, min_z + 0.28 * h],
        "RightFoot": [cx + 0.09 * h, cy - 0.05 * h, min_z + 0.04 * h],
        "RightToeBase": [cx + 0.09 * h, cy - 0.12 * h, min_z + 0.02 * h],
        "CoatFront": [cx, cy - 0.06 * h, min_z + 0.35 * h],
        "CoatBack": [cx, cy + 0.06 * h, min_z + 0.35 * h],
    }

    for jname, loc in joints.items():
        add_dot(jname, loc, (1, 0.2, 0.1, 1) if "Coat" not in jname else (0.2, 0.8, 1, 1))

    write_json(base / "exports" / "joints.json", {"units": "meters", "joints": joints})
    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_joints.blend"))

    scale = frame_objects([obj])
    for view in ("front", "side"):
        render_view(base / "renders" / f"joints_{view}.png", view, px=768, ortho_scale=scale, grid=True)
    log(f"wrote {len(joints)} joints (5 cm grid + axis markers)")


if __name__ == "__main__":
    main()
