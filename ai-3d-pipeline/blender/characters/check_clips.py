"""Step 14 — numeric clip QC: foot slide, floor penetration, hip range, loop delta."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import render_view, frame_objects  # noqa: E402
from blender.common.utils import log, pipeline_args, write_json  # noqa: E402


def bone_world(arm, name: str) -> Vector:
    pb = arm.pose.bones[name]
    return arm.matrix_world @ pb.matrix.to_translation()


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    bpy.ops.wm.open_mainfile(filepath=str(base / "exports" / f"{name}_clips.blend"))
    arm = bpy.data.objects["Armature"]
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    scene = bpy.context.scene

    reports = {}
    for track in arm.animation_data.nla_tracks if arm.animation_data else []:
        if not track.strips:
            continue
        strip = track.strips[0]
        action = strip.action
        arm.animation_data.action = action
        start, end = int(action.frame_range[0]), int(action.frame_range[1])
        foot_positions = {"LeftFoot": [], "RightFoot": []}
        hip_z = []
        min_vert_z = []

        for f in range(start, end + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            for foot in foot_positions:
                if foot in arm.pose.bones:
                    foot_positions[foot].append(bone_world(arm, foot))
            if "Hips" in arm.pose.bones:
                hip_z.append(bone_world(arm, "Hips").z)
            deps = bpy.context.evaluated_depsgraph_get()
            ev = mesh.evaluated_get(deps)
            em = ev.to_mesh()
            min_vert_z.append(min((mesh.matrix_world @ v.co).z for v in em.vertices))
            ev.to_mesh_clear()

        def slide(positions):
            if len(positions) < 2:
                return 0.0
            # approximate planted slide: when z near min, sum horizontal delta
            zs = [p.z for p in positions]
            floor = min(zs) + 0.02
            total = 0.0
            for i in range(1, len(positions)):
                if positions[i].z <= floor and positions[i - 1].z <= floor:
                    d = positions[i] - positions[i - 1]
                    total += (d.x * d.x + d.y * d.y) ** 0.5
            return total

        # loop delta
        scene.frame_set(start)
        bpy.context.view_layer.update()
        first = {b.name: (b.location.copy(), b.rotation_euler.copy()) for b in arm.pose.bones}
        scene.frame_set(end)
        bpy.context.view_layer.update()
        loop_err = 0.0
        for b in arm.pose.bones:
            loc0, rot0 = first[b.name]
            loop_err += (b.location - loc0).length
            loop_err += (Vector(b.rotation_euler) - Vector(rot0)).length

        reports[track.name] = {
            "frames": end - start + 1,
            "foot_slide_L_m": round(slide(foot_positions["LeftFoot"]), 4),
            "foot_slide_R_m": round(slide(foot_positions["RightFoot"]), 4),
            "lowest_vertex_z": round(min(min_vert_z), 4),
            "hips_z_range": [round(min(hip_z), 4), round(max(hip_z), 4)] if hip_z else None,
            "loop_delta": round(loop_err, 5),
            "failures": [],
        }
        r = reports[track.name]
        if r["lowest_vertex_z"] < -0.005:
            r["failures"].append("floor_penetration")
        if r["foot_slide_L_m"] > 0.05 or r["foot_slide_R_m"] > 0.05:
            r["failures"].append("foot_slide")
        if r["loop_delta"] > 0.05:
            r["failures"].append("loop_mismatch")

        # frame sheet mid
        mid = (start + end) // 2
        scene.frame_set(mid)
        scale = frame_objects([mesh])
        render_view(base / "renders" / f"clip_{track.name}_mid.png", "three_quarter", px=512, ortho_scale=scale)

    arm.animation_data.action = None
    write_json(base / "exports" / "clip_qc_report.json", reports)
    log(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
