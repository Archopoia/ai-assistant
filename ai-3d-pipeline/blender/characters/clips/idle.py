"""Step 13 — 2s idle loop, breathing + weight shift, 30 fps."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from blender.common.utils import log, pipeline_args  # noqa: E402

FPS = 30
DURATION = 2.0


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    bpy.ops.wm.open_mainfile(filepath=str(base / "exports" / f"{name}_rigged.blend"))
    arm = bpy.data.objects["Armature"]
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    scene = bpy.context.scene
    scene.render.fps = FPS
    frames = int(DURATION * FPS)
    scene.frame_start = 1
    scene.frame_end = frames

    # clear old action
    if arm.animation_data:
        arm.animation_data_clear()
    arm.animation_data_create()
    action = bpy.data.actions.new("idle")
    arm.animation_data.action = action

    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    for f in range(1, frames + 1):
        t = (f - 1) / frames
        breath = math.sin(t * math.pi * 2) * 0.02
        shift = math.sin(t * math.pi * 2) * 0.015
        scene.frame_set(f)

        hips = arm.pose.bones.get("Hips")
        if hips:
            hips.location = (shift, 0, breath * 0.5)
            hips.keyframe_insert("location", frame=f)

        spine = arm.pose.bones.get("Spine1")
        if spine:
            spine.rotation_euler = (breath * 0.4, 0, 0)
            spine.keyframe_insert("rotation_euler", frame=f)

        head = arm.pose.bones.get("Head")
        if head:
            head.rotation_euler = (breath * 0.2, 0, shift * 0.5)
            head.keyframe_insert("rotation_euler", frame=f)

    # match first/last for loop continuity
    scene.frame_set(1)
    for pb in ("Hips", "Spine1", "Head"):
        bone = arm.pose.bones.get(pb)
        if not bone:
            continue
        bone.keyframe_insert("location", frame=frames)
        bone.keyframe_insert("rotation_euler", frame=frames)

    out = base / "clips"
    out.mkdir(parents=True, exist_ok=True)
    # push down to NLA strip named idle, clear active action so clips coexist
    track = arm.animation_data.nla_tracks.new()
    track.name = "idle"
    track.strips.new("idle", 1, action)
    arm.animation_data.action = None

    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_clips.blend"))
    log(f"idle action {frames} frames @ {FPS}fps")


if __name__ == "__main__":
    main()
