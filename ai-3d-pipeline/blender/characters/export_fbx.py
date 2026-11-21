"""
Step 15 — export character.fbx with mesh, armature, clips.
Apply Transform OFF, Add Leaf Bones OFF.
Re-import probe + print counts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.utils import log, pipeline_args, triangle_count, write_json  # noqa: E402


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    src = base / "exports" / f"{name}_clips.blend"
    if not src.exists():
        src = base / "exports" / f"{name}_rigged.blend"
    bpy.ops.wm.open_mainfile(filepath=str(src))

    # probe cube for scale check
    bpy.ops.mesh.primitive_cube_add(size=0.1, location=(0.6, 0, 0.05))
    probe = bpy.context.active_object
    probe.name = "PROBE_10cm"

    out = base / "exports" / f"{name}.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(out),
        use_selection=False,
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=True,
        apply_scale_options="FBX_SCALE_ALL",
        # CRITICAL: do not use apply_transform with armatures
        use_armature_deform_only=True,
    )

    # also GLB mesh-only hero for web
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "PROBE_10cm")
    arm = bpy.data.objects.get("Armature")
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    if arm:
        arm.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(base / "exports" / f"{name}.glb"),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
    )

    bones = len(arm.data.bones) if arm else 0
    bbox = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    height = max(v.z for v in bbox) - min(v.z for v in bbox)
    report = {
        "fbx": str(out.relative_to(ROOT)),
        "bones": bones,
        "triangles": triangle_count(mesh),
        "height_m": round(height, 4),
        "probe": "PROBE_10cm cube included for importer scale check",
        "unity": "Humanoid if biped; set Loop Time on clips",
        "roblox": "Import 3D, Rig Custom, Zero Influence Bones on, max 4 bones/vertex",
    }
    write_json(base / "exports" / "export_report.json", report)
    log(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
