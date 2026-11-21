"""
Step 08 — clean generator GLB: orient, feet on floor, merge, normals,
decimate hero + crowd, bake base colour + normal from hi → lo when possible.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Euler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blender.common.render import frame_objects, render_view  # noqa: E402
from blender.common.utils import (  # noqa: E402
    clear_scene,
    log,
    pipeline_args,
    triangle_count,
    write_json,
)


def get_mesh() -> bpy.types.Object:
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh after import")
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
    return bpy.context.active_object


def orient_and_scale(obj: bpy.types.Object, height_m: float) -> None:
    obj.rotation_euler = Euler((0, 0, -math.pi / 2), "XYZ")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(v.z for v in bbox)
    obj.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cur_h = max(v.z for v in bbox) - min(v.z for v in bbox)
    if cur_h > 1e-6:
        s = height_m / cur_h
        obj.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cx = (min(v.x for v in bbox) + max(v.x for v in bbox)) / 2
    cy = (min(v.y for v in bbox) + max(v.y for v in bbox)) / 2
    obj.location.x -= cx
    obj.location.y -= cy
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def merge_and_normals(obj: bpy.types.Object) -> dict:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_loose()
    bpy.ops.object.mode_set(mode="OBJECT")
    loose = sum(1 for v in obj.data.vertices if v.select)
    return {"loose_verts": loose, "triangles": triangle_count(obj)}


def decimate_copy(obj: bpy.types.Object, budget: int, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()
    low = bpy.context.active_object
    low.name = name
    tris = max(triangle_count(low), 1)
    ratio = min(1.0, budget / tris)
    mod = low.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return low


def ensure_uv(obj: bpy.types.Object) -> None:
    if obj.data.uv_layers:
        return
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.03)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_maps(hi: bpy.types.Object, lo: bpy.types.Object, out_dir: Path, size: int = 1024) -> dict:
    """Bake colour + normal from hi onto lo (tutorial step 08.4)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_uv(lo)
    ensure_uv(hi)

    # Cycles bake
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 8
    bpy.context.scene.cycles.bake_type = "NORMAL"

    def _img(name: str):
        img = bpy.data.images.new(name, width=size, height=size, alpha=True)
        return img

    results = {}
    try:
        # material on lo with image nodes
        mat = bpy.data.materials.new(name=f"{lo.name}_bake")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out_n = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs["BSDF"], out_n.inputs["Surface"])
        tex_c = nt.nodes.new("ShaderNodeTexImage")
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        img_c = _img(f"{lo.name}_basecolor")
        img_n = _img(f"{lo.name}_normal")
        tex_c.image = img_c
        tex_n.image = img_n
        if lo.data.materials:
            lo.data.materials[0] = mat
        else:
            lo.data.materials.append(mat)

        # select hi then lo active for selected-to-active
        bpy.ops.object.select_all(action="DESELECT")
        hi.hide_render = False
        hi.hide_viewport = False
        hi.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo

        bpy.context.scene.render.bake.use_selected_to_active = True
        bpy.context.scene.render.bake.cage_extrusion = 0.05
        bpy.context.scene.render.bake.margin = 4

        # base colour / diffuse
        nt.nodes.active = tex_c
        bpy.context.scene.cycles.bake_type = "DIFFUSE"
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True
        bpy.ops.object.bake(type="DIFFUSE")
        path_c = out_dir / f"{lo.name}_basecolor.png"
        img_c.filepath_raw = str(path_c)
        img_c.file_format = "PNG"
        img_c.save()
        results["basecolor"] = str(path_c)

        nt.nodes.active = tex_n
        bpy.context.scene.cycles.bake_type = "NORMAL"
        bpy.ops.object.bake(type="NORMAL")
        path_n = out_dir / f"{lo.name}_normal.png"
        img_n.filepath_raw = str(path_n)
        img_n.file_format = "PNG"
        img_n.save()
        results["normal"] = str(path_n)

        # hook textures into principled
        nt.links.new(tex_c.outputs["Color"], bsdf.inputs["Base Color"])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    except Exception as e:
        results["bake_error"] = str(e)
        log(f"bake skipped/partial: {e}")
    return results


def main() -> None:
    args = pipeline_args()
    name = args["asset"]
    base = ROOT / "examples" / "characters" / name
    src = Path(args.get("input", base / "exports" / "raw.glb"))
    height = float(args.get("height_m", 1.15))
    hero_budget = int(args.get("hero_triangles", 40000))
    crowd_budget = int(args.get("crowd_triangles", 3000))

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(src))
    obj = get_mesh()
    obj.name = name
    orient_and_scale(obj, height)
    stats = merge_and_normals(obj)

    hero = decimate_copy(obj, hero_budget, f"{name}_hero")
    crowd = decimate_copy(obj, crowd_budget, f"{name}_crowd")

    exports = base / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    bake = {}
    if triangle_count(obj) > triangle_count(hero) + 50:
        bake = bake_maps(obj, hero, exports / "textures")
    else:
        ensure_uv(hero)

    if obj.name != hero.name:
        obj.hide_render = True
        obj.hide_viewport = True

    bpy.ops.object.select_all(action="DESELECT")
    hero.select_set(True)
    bpy.context.view_layer.objects.active = hero
    bpy.ops.export_scene.gltf(filepath=str(exports / f"{name}_clean.glb"), export_format="GLB", use_selection=True)
    bpy.ops.object.select_all(action="DESELECT")
    crowd.select_set(True)
    bpy.context.view_layer.objects.active = crowd
    bpy.ops.export_scene.gltf(filepath=str(exports / f"{name}_crowd.glb"), export_format="GLB", use_selection=True)

    crowd.hide_render = True
    crowd.hide_viewport = True
    hero.hide_render = False
    hero.hide_viewport = False
    scale = frame_objects([hero])
    for view in ("front", "side", "back"):
        render_view(base / "renders" / f"clean_{view}.png", view, px=768, ortho_scale=scale, grid=True)

    report = {
        **stats,
        "hero_triangles": triangle_count(hero),
        "crowd_triangles": triangle_count(crowd),
        "height_m": height,
        "bake": bake,
    }
    write_json(exports / "clean_report.json", report)
    log(json.dumps(report))


if __name__ == "__main__":
    main()
