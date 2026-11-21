"""Shared helpers for Blender scripts (run inside Blender)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


def pipeline_args() -> dict:
    return json.loads(os.environ.get("PIPELINE_ARGS", "{}"))


def pipeline_root() -> Path:
    return Path(os.environ.get("PIPELINE_ROOT", "."))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        if block.users == 0:
            bpy.data.materials.remove(block)


def flat_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.55
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def apply_all_modifiers(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            obj.modifiers.remove(mod)


def triangle_count(obj: bpy.types.Object) -> int:
    mesh = obj.data
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def set_origin_base_center(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    # Move so lowest Z sits on 0 and XY centered
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(v.z for v in bbox)
    cx = (min(v.x for v in bbox) + max(v.x for v in bbox)) / 2
    cy = (min(v.y for v in bbox) + max(v.y for v in bbox)) / 2
    obj.location.x -= cx
    obj.location.y -= cy
    obj.location.z -= min_z
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)
