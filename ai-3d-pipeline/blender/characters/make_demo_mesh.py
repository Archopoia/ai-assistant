"""
Create a free A-pose placeholder character (no generator / no API) for pipeline smoke tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.utils import clear_scene, flat_material, log, pipeline_args, set_origin_base_center  # noqa: E402


def add_box(name, loc, scale, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    mat = flat_material(f"m_{name}", color)
    obj.data.materials.append(mat)
    return obj


def main() -> None:
    args = pipeline_args()
    name = args.get("asset", "demo")
    base = ROOT / "examples" / "characters" / name
    exports = base / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    clear_scene()
    skin = (0.9, 0.75, 0.65, 1)
    cloth = (0.2, 0.35, 0.55, 1)
    coat = (0.12, 0.12, 0.16, 1)
    pants = (0.25, 0.25, 0.3, 1)

    parts = [
        add_box("torso", (0, 0, 0.85), (0.35, 0.2, 0.45), cloth),
        add_box("head", (0, 0, 1.25), (0.22, 0.22, 0.24), skin),
        add_box("arm_L", (-0.35, 0, 0.85), (0.12, 0.12, 0.4), cloth),
        add_box("arm_R", (0.35, 0, 0.85), (0.12, 0.12, 0.4), cloth),
        add_box("hand_L", (-0.35, -0.05, 0.58), (0.1, 0.08, 0.1), skin),
        add_box("hand_R", (0.35, -0.05, 0.58), (0.1, 0.08, 0.1), skin),
        add_box("leg_L", (-0.1, 0, 0.35), (0.14, 0.14, 0.45), pants),
        add_box("leg_R", (0.1, 0, 0.35), (0.14, 0.14, 0.45), pants),
        add_box("coat", (0, 0.02, 0.55), (0.4, 0.18, 0.35), coat),
    ]
    # A-pose: rotate arms down ~45 via location already offset

    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    final = bpy.context.active_object
    final.name = name
    set_origin_base_center(final)

    raw = exports / "raw.glb"
    bpy.ops.export_scene.gltf(filepath=str(raw), export_format="GLB")
    log(f"demo character → {raw}")


if __name__ == "__main__":
    main()
