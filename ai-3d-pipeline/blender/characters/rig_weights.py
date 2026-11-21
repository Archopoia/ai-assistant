"""
Step 11 — build Mixamo armature from joints.json, bind, then apply clothing weight rules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.utils import log, pipeline_args, write_json  # noqa: E402

# parent map (child → parent)
HIERARCHY = [
    ("Hips", None),
    ("Spine", "Hips"),
    ("Spine1", "Spine"),
    ("Spine2", "Spine1"),
    ("Neck", "Spine2"),
    ("Head", "Neck"),
    ("LeftShoulder", "Spine2"),
    ("LeftArm", "LeftShoulder"),
    ("LeftForeArm", "LeftArm"),
    ("LeftHand", "LeftForeArm"),
    ("RightShoulder", "Spine2"),
    ("RightArm", "RightShoulder"),
    ("RightForeArm", "RightArm"),
    ("RightHand", "RightForeArm"),
    ("LeftUpLeg", "Hips"),
    ("LeftLeg", "LeftUpLeg"),
    ("LeftFoot", "LeftLeg"),
    ("LeftToeBase", "LeftFoot"),
    ("RightUpLeg", "Hips"),
    ("RightLeg", "RightUpLeg"),
    ("RightFoot", "RightLeg"),
    ("RightToeBase", "RightFoot"),
    ("CoatFront", "Hips"),
    ("CoatBack", "Hips"),
]

ARM_BONES = {
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
}


def build_armature(joints: dict) -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.active_object
    arm.name = "Armature"
    eb = arm.data.edit_bones
    # remove default bone
    for b in list(eb):
        eb.remove(b)

    bones = {}
    for name, parent in HIERARCHY:
        if name not in joints:
            continue
        bone = eb.new(name)
        head = Vector(joints[name])
        # tip toward child or slight up
        children = [c for c, p in HIERARCHY if p == name and c in joints]
        if children:
            tip = Vector(joints[children[0]])
        else:
            tip = head + Vector((0, 0, 0.05))
        if (tip - head).length < 1e-4:
            tip = head + Vector((0, 0, 0.05))
        bone.head = head
        bone.tail = tip
        bones[name] = bone

    for name, parent in HIERARCHY:
        if name in bones and parent and parent in bones:
            bones[name].parent = bones[parent]
            bones[name].use_connect = False

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def vg_vertices(obj, group_name: str) -> list[int]:
    if group_name not in obj.vertex_groups:
        return []
    g = obj.vertex_groups[group_name]
    idxs = []
    for v in obj.data.vertices:
        for gref in v.groups:
            if gref.group == g.index and gref.weight > 0.1:
                idxs.append(v.index)
                break
    return idxs


def _in_group(obj, group_index: int, vid: int) -> bool:
    for gref in obj.data.vertices[vid].groups:
        if gref.group == group_index:
            return True
    return False


def set_exclusive(obj, verts: list[int], bone: str) -> None:
    bone_names = {n for n, _ in HIERARCHY} | {g.name for g in obj.vertex_groups if g.name.startswith("Coat")}
    if bone not in obj.vertex_groups:
        obj.vertex_groups.new(name=bone)
    target = obj.vertex_groups[bone]
    for v in verts:
        for g in obj.vertex_groups:
            if g.name in bone_names and _in_group(obj, g.index, v):
                g.remove([v])
        target.add([v], 1.0, "REPLACE")


def zero_arm_weights_on(obj, verts: list[int]) -> None:
    for bone in ARM_BONES:
        if bone not in obj.vertex_groups:
            continue
        g = obj.vertex_groups[bone]
        for v in verts:
            if _in_group(obj, g.index, v):
                g.add([v], 0.0, "REPLACE")


def normalize_max4(obj) -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    # prune to 4 influences
    for v in obj.data.vertices:
        weights = [(g.group, g.weight) for g in v.groups if g.weight > 0]
        weights.sort(key=lambda x: x[1], reverse=True)
        keep = {gid for gid, _ in weights[:4]}
        for gid, _ in weights[4:]:
            for vg in obj.vertex_groups:
                if vg.index == gid:
                    vg.remove([v.index])
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    bpy.ops.wm.open_mainfile(filepath=str(base / "exports" / f"{name}_joints.blend"))

    # remove joint dots
    for o in list(bpy.data.objects):
        if o.name.startswith("joint_"):
            bpy.data.objects.remove(o, do_unlink=True)

    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    joints = json.loads((base / "exports" / "joints.json").read_text())["joints"]
    arm = build_armature(joints)

    # bind
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # ensure deform groups exist
    for bname, _ in HIERARCHY:
        if bname not in obj.vertex_groups:
            obj.vertex_groups.new(name=bname)

    # rules
    torso = vg_vertices(obj, "torso") + vg_vertices(obj, "coat")
    zero_arm_weights_on(obj, torso)

    set_exclusive(obj, vg_vertices(obj, "head"), "Head")
    set_exclusive(obj, vg_vertices(obj, "hand_L"), "LeftHand")
    set_exclusive(obj, vg_vertices(obj, "hand_R"), "RightHand")

    # coat skirt → cloth bones by Y
    coat_verts = vg_vertices(obj, "coat")
    for vi in coat_verts:
        world = obj.matrix_world @ obj.data.vertices[vi].co
        bone = "CoatFront" if world.y < 0 else "CoatBack"
        set_exclusive(obj, [vi], bone)

    normalize_max4(obj)

    bpy.ops.wm.save_as_mainfile(filepath=str(base / "exports" / f"{name}_rigged.blend"))
    # rest pose export
    bpy.ops.export_scene.fbx(
        filepath=str(base / "exports" / f"{name}_rigged.fbx"),
        use_selection=False,
        add_leaf_bones=False,
        bake_anim=False,
        apply_scale_options="FBX_SCALE_ALL",
    )
    write_json(base / "exports" / "rig_report.json", {"bones": [n for n, _ in HIERARCHY], "mesh": obj.name})
    log("rig + weight rules applied")


if __name__ == "__main__":
    main()
