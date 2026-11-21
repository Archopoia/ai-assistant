"""
Step 12 — pose tests + stretch metrics; max 3 rounds expected from CLI.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import frame_objects, render_view  # noqa: E402
from blender.common.utils import log, pipeline_args, write_json  # noqa: E402


POSES = {
    "arms_up_90": {
        "LeftArm": (0, 0, math.radians(90)),
        "RightArm": (0, 0, math.radians(-90)),
    },
    "arms_forward_60": {
        "LeftArm": (math.radians(-60), 0, 0),
        "RightArm": (math.radians(-60), 0, 0),
    },
    "step_L": {
        "LeftUpLeg": (math.radians(-25), 0, 0),
        "LeftLeg": (math.radians(20), 0, 0),
        "RightUpLeg": (math.radians(10), 0, 0),
    },
    "step_R": {
        "RightUpLeg": (math.radians(-25), 0, 0),
        "RightLeg": (math.radians(20), 0, 0),
        "LeftUpLeg": (math.radians(10), 0, 0),
    },
    "head_turn_60": {
        "Head": (0, 0, math.radians(60)),
        "Neck": (0, 0, math.radians(20)),
    },
}


def rest_edge_lengths(obj) -> dict[tuple[int, int], float]:
    mesh = obj.data
    lengths = {}
    for e in mesh.edges:
        a, b = e.vertices
        lengths[(a, b)] = (mesh.vertices[a].co - mesh.vertices[b].co).length
    return lengths


def stretch_report(obj, rest: dict) -> dict:
    mesh = obj.data
    # need deformed coords — use depsgraph
    deps = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(deps)
    eval_mesh = eval_obj.to_mesh()
    worst = []
    max_ratio = 1.0
    for (a, b), rest_len in rest.items():
        if rest_len < 1e-8:
            continue
        cur = (eval_mesh.vertices[a].co - eval_mesh.vertices[b].co).length
        ratio = cur / rest_len
        if ratio > max_ratio:
            max_ratio = ratio
        worst.append((ratio, a, b))
    eval_obj.to_mesh_clear()
    worst.sort(reverse=True)
    top = []
    for ratio, a, b in worst[:10]:
        # bones influencing a
        bones = []
        for g in obj.data.vertices[a].groups:
            vg = obj.vertex_groups[g.group]
            bones.append({"bone": vg.name, "w": round(g.weight, 3)})
        top.append({"ratio": round(ratio, 2), "v": a, "bones": bones})
    return {"max_stretch": round(max_ratio, 2), "worst": top}


def apply_pose(arm, pose_dict):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    for bname, euler in pose_dict.items():
        if bname in arm.pose.bones:
            arm.pose.bones[bname].rotation_euler = euler
    bpy.context.view_layer.update()


def clear_pose(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    bpy.ops.object.mode_set(mode="OBJECT")


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    bpy.ops.wm.open_mainfile(filepath=str(base / "exports" / f"{name}_rigged.blend"))
    arm = bpy.data.objects["Armature"]
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")

    clear_pose(arm)
    rest = rest_edge_lengths(obj)
    reports = {}
    scale = frame_objects([obj])

    for pname, pdata in POSES.items():
        apply_pose(arm, pdata)
        reports[pname] = stretch_report(obj, rest)
        for view in ("front", "side"):
            render_view(base / "renders" / f"pose_{pname}_{view}.png", view, px=512, ortho_scale=scale)
        log(f"{pname}: max stretch {reports[pname]['max_stretch']}x")

    clear_pose(arm)
    write_json(base / "exports" / "pose_test_report.json", reports)
    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_rigged.blend"))


if __name__ == "__main__":
    main()
