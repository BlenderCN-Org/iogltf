from typing import Tuple, List

from . import gltftypes
from . import gltf_buffer
from .import_manager import ImportManager

import bpy
from progress_report import ProgressReport


def _create_mesh(progress: ProgressReport, manager: ImportManager,
                 mesh: gltftypes.Mesh)->Tuple[bpy.types.Mesh, gltf_buffer.VertexBuffer]:
    blender_mesh = bpy.data.meshes.new(mesh.name)
    materials = [manager.materials[prim.material] for prim in mesh.primitives]
    for m in materials:
        blender_mesh.materials.append(m)

    attributes = gltf_buffer.VertexBuffer(manager, mesh)

    blender_mesh.vertices.add(len(attributes.pos)/3)
    blender_mesh.vertices.foreach_set(
        "co", attributes.pos)
    blender_mesh.vertices.foreach_set(
        "normal", attributes.nom)

    blender_mesh.loops.add(len(attributes.indices))
    blender_mesh.loops.foreach_set("vertex_index", attributes.indices)

    triangle_count = int(len(attributes.indices) / 3)
    blender_mesh.polygons.add(triangle_count)
    starts = [i * 3 for i in range(triangle_count)]
    blender_mesh.polygons.foreach_set("loop_start", starts)
    total = [3 for _ in range(triangle_count)]
    blender_mesh.polygons.foreach_set("loop_total", total)

    blen_uvs = blender_mesh.uv_layers.new()
    for blen_poly in blender_mesh.polygons:
        blen_poly.use_smooth = True
        blen_poly.material_index = attributes.get_submesh_from_face(
            blen_poly.index)
        for lidx in blen_poly.loop_indices:
            index = attributes.indices[lidx]
            # vertex uv to face uv
            uv = attributes.uv[index]
            blen_uvs.data[lidx].uv = (
                uv.x, uv.y)  # vertical flip uv

    # *Very* important to not remove lnors here!
    blender_mesh.validate(clean_customdata=False)
    blender_mesh.update()

    progress.step()
    return blender_mesh, attributes


def load_meshes(progress: ProgressReport,
                manager: ImportManager)->List[Tuple[bpy.types.Mesh, gltf_buffer.VertexBuffer]]:

    progress.enter_substeps(len(manager.gltf.meshes), "Loading meshes...")
    meshes = [_create_mesh(progress, manager, mesh)
              for mesh in manager.gltf.meshes]
    progress.leave_substeps()
    return meshes
