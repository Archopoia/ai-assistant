"""
Procedural building generator — free city props (step 05 buildings route).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import frame_objects, render_view  # noqa: E402
from blender.common.utils import (  # noqa: E402
    apply_all_modifiers,
    clear_scene,
    flat_material,
    log,
    pipeline_args,
    set_origin_base_center,
    triangle_count,
)


PALETTES = [
    (0.72, 0.55, 0.42, 1),
    (0.45, 0.52, 0.58, 1),
    (0.62, 0.48, 0.38, 1),
    (0.78, 0.78, 0.74, 1),
    (0.35, 0.42, 0.48, 1),
]


def add_box(name, loc, scale, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    mat = flat_material(f"mat_{name}_{id(obj)}", color)
    obj.data.materials.append(mat)
    return obj


def building(seed: int, width=6.0, depth=8.0, floors=3, roof="gable", colour=None):
    rng = random.Random(seed)
    colour = colour or PALETTES[rng.randrange(len(PALETTES))]
    floor_h = 3.0
    height = floors * floor_h
    body = add_box("body", (0, 0, height / 2), (width, depth, height), colour)

    # windows
    win_col = (0.55, 0.75, 0.9, 1)
    margin = 0.8
    for f in range(floors):
        z = f * floor_h + floor_h * 0.55
        for side, axis in (("front", -1), ("back", 1)):
            n = max(1, int(width // 2))
            for i in range(n):
                x = -width / 2 + margin + (i + 0.5) * ((width - 2 * margin) / n)
                y = axis * (depth / 2 + 0.05)
                add_box(f"win_{side}_{f}_{i}", (x, y, z), (0.9, 0.08, 1.2), win_col)

    # door
    door_col = (0.25, 0.15, 0.1, 1)
    add_box("door", (0, -depth / 2 - 0.06, 1.1), (1.1, 0.1, 2.2), door_col)

    # roof
    roof_col = (0.25, 0.28, 0.3, 1)
    if roof == "flat":
        add_box("roof", (0, 0, height + 0.15), (width + 0.3, depth + 0.3, 0.3), roof_col)
    else:
        # simple gable as a stretched cube rotated — low poly
        roof_obj = add_box("roof", (0, 0, height + 0.8), (width + 0.4, depth + 0.2, 1.6), roof_col)
        roof_obj.scale.z = 0.5
        bpy.ops.object.transform_apply(scale=True)

    # join
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    final = bpy.context.active_object
    final.name = f"building_{seed}"
    set_origin_base_center(final)
    return final


def main() -> None:
    args = pipeline_args()
    count = int(args.get("count", 10))
    out_dir = ROOT / "examples" / "props" / "buildings" / "exports"
    renders = ROOT / "examples" / "props" / "buildings" / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)

    variants = []
    for i in range(count):
        clear_scene()
        seed = 1000 + i
        floors = 2 + (i % 4)
        width = 5 + (i % 3)
        depth = 6 + (i % 4)
        roof = "flat" if i % 3 == 0 else "gable"
        obj = building(seed, width=width, depth=depth, floors=floors, roof=roof)
        path = out_dir / f"building_{seed}.glb"
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
        variants.append({"seed": seed, "triangles": triangle_count(obj), "glb": str(path)})
        scale = frame_objects([obj])
        render_view(renders / f"building_{seed}.png", "three_quarter", px=512, ortho_scale=scale)
        log(f"building {seed}: {triangle_count(obj)} tris")

    log(f"wrote {len(variants)} buildings to {out_dir}")


if __name__ == "__main__":
    main()
