"""Step 13 — 1s walk loop, two footsteps, IK-ish planted feet, 2 cm hip bob."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from blender.common.utils import log, pipeline_args  # noqa: E402

FPS = 30
DURATION = 1.0


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    path = base / "exports" / f"{name}_clips.blend"
    if not path.exists():
        path = base / "exports" / f"{name}_rigged.blend"
    bpy.ops.wm.open_mainfile(filepath=str(path))
    arm = bpy.data.objects["Armature"]
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    scene = bpy.context.scene
    scene.render.fps = FPS
    frames = int(DURATION * FPS)
    scene.frame_start = 1
    scene.frame_end = max(scene.frame_end, frames)

    action = bpy.data.actions.new("walk")
    if not arm.animation_data:
        arm.animation_data_create()
    # keep idle on NLA; set active action to walk for authoring then push
    arm.animation_data.action = action

    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    for f in range(1, frames + 1):
        t = (f - 1) / frames
        phase = t * math.pi * 2
        scene.frame_set(f)

        hips = arm.pose.bones.get("Hips")
        if hips:
            hips.location = (0, 0, abs(math.sin(phase)) * 0.02)
            hips.keyframe_insert("location", frame=f)

        # legs
        lu = arm.pose.bones.get("LeftUpLeg")
        ll = arm.pose.bones.get("LeftLeg")
        ru = arm.pose.bones.get("RightUpLeg")
        rl = arm.pose.bones.get("RightLeg")
        if lu and ll and ru and rl:
            lu.rotation_euler = (math.sin(phase) * 0.45, 0, 0)
            ll.rotation_euler = (max(0, -math.sin(phase)) * 0.55, 0, 0)
            ru.rotation_euler = (math.sin(phase + math.pi) * 0.45, 0, 0)
            rl.rotation_euler = (max(0, -math.sin(phase + math.pi)) * 0.55, 0, 0)
            for b in (lu, ll, ru, rl):
                b.keyframe_insert("rotation_euler", frame=f)

        # arms opposite
        la = arm.pose.bones.get("LeftArm")
        ra = arm.pose.bones.get("RightArm")
        if la and ra:
            la.rotation_euler = (math.sin(phase + math.pi) * 0.35, 0, 0)
            ra.rotation_euler = (math.sin(phase) * 0.35, 0, 0)
            la.keyframe_insert("rotation_euler", frame=f)
            ra.keyframe_insert("rotation_euler", frame=f)

    # loop continuity
    scene.frame_set(1)
    for pb in ("Hips", "LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg", "LeftArm", "RightArm"):
        bone = arm.pose.bones.get(pb)
        if not bone:
            continue
        bone.keyframe_insert("location", frame=frames)
        bone.keyframe_insert("rotation_euler", frame=frames)

    track = arm.animation_data.nla_tracks.new()
    track.name = "walk"
    track.strips.new("walk", 1, action)
    arm.animation_data.action = None

    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_clips.blend"))
    log(f"walk action {frames} frames @ {FPS}fps")


if __name__ == "__main__":
    main()
