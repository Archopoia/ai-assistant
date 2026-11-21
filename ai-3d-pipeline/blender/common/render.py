"""Orthographic renders for QC."""
from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


def add_cm_grid(extent_m: float = 1.5, step_m: float = 0.05) -> list:
    """Guide step 08/10 — 5 cm grid on XY (ground) for scale checks."""
    created = []
    # clear old
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Grid5cm"):
            bpy.data.objects.remove(obj, do_unlink=True)
    n = int(extent_m / step_m)
    for i in range(-n, n + 1):
        for axis in ("x", "y"):
            mesh = bpy.data.meshes.new(f"Grid5cm_{axis}_{i}")
            if axis == "x":
                verts = [(-extent_m, i * step_m, 0), (extent_m, i * step_m, 0)]
            else:
                verts = [(i * step_m, -extent_m, 0), (i * step_m, extent_m, 0)]
            mesh.from_pydata(verts, [(0, 1)], [])
            obj = bpy.data.objects.new(f"Grid5cm_{axis}_{i}", mesh)
            bpy.context.collection.objects.link(obj)
            created.append(obj)
    # labelled axes
    for name, loc, color in (
        ("Grid5cm_axis_X", (extent_m * 0.9, 0, 0.02), (1, 0.2, 0.2, 1)),
        ("Grid5cm_axis_Y", (0, extent_m * 0.9, 0.02), (0.2, 1, 0.2, 1)),
        ("Grid5cm_axis_Z", (0, 0, extent_m * 0.5), (0.2, 0.4, 1, 1)),
    ):
        bpy.ops.mesh.primitive_cube_add(size=0.04, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        mat = bpy.data.materials.new(name=f"mat_{name}")
        mat.use_nodes = False
        mat.diffuse_color = color
        obj.data.materials.append(mat)
        created.append(obj)
    return created


def setup_ortho_camera(view: str = "side", size: float = 2.0) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("PipelineCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size
    cam = bpy.data.objects.new("PipelineCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    if view == "front":
        cam.location = (0, -5, 1)
        cam.rotation_euler = (1.5708, 0, 0)
    elif view == "side":
        cam.location = (5, 0, 1)
        cam.rotation_euler = (1.5708, 0, 1.5708)
    elif view == "back":
        cam.location = (0, 5, 1)
        cam.rotation_euler = (1.5708, 0, 3.14159)
    elif view == "top":
        cam.location = (0, 0, 5)
        cam.rotation_euler = (0, 0, 0)
    else:  # three_quarter
        cam.location = (3.5, -3.5, 2.2)
        cam.rotation_euler = (1.1, 0, 0.785)
        cam_data.type = "PERSP"
        cam_data.lens = 50
    return cam


def setup_flat_light() -> None:
    for name, loc, energy in (
        ("Key", (3, -3, 4), 400),
        ("Fill", (-3, -1, 2), 150),
        ("Rim", (0, 3, 3), 200),
    ):
        light = bpy.data.lights.new(name, type="AREA")
        light.energy = energy
        obj = bpy.data.objects.new(name, light)
        obj.location = loc
        bpy.context.collection.objects.link(obj)


def render_view(
    path: Path,
    view: str = "side",
    px: int = 768,
    ortho_scale: float = 2.0,
    *,
    grid: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # remove old cameras/lights named Pipeline*
    for obj in list(bpy.data.objects):
        if obj.name.startswith("PipelineCam") or obj.name in {"Key", "Fill", "Rim"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    grid_objs = add_cm_grid(extent_m=max(1.0, ortho_scale), step_m=0.05) if grid else []
    setup_ortho_camera(view, size=ortho_scale)
    setup_flat_light()

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = px
    scene.render.resolution_y = px
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    for obj in grid_objs:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except ReferenceError:
            pass
    return path


def frame_objects(objects) -> float:
    coords = []
    for obj in objects:
        for corner in obj.bound_box:
            coords.append(obj.matrix_world @ Vector(corner))
    if not coords:
        return 2.0
    xs = [v.x for v in coords]
    ys = [v.y for v in coords]
    zs = [v.z for v in coords]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 0.1)
    return span * 1.4
