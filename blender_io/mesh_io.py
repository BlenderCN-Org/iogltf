from typing import Tuple, List

import bpy
from progress_report import ProgressReport

from .. import gltftypes, gltf_buffer
from .import_manager import ImportManager


def _create_mesh(progress: ProgressReport, manager: ImportManager,
                 mesh: gltftypes.Mesh)->Tuple[bpy.types.Mesh, gltf_buffer.VertexBuffer]:
    blender_mesh = bpy.data.meshes.new(mesh.name)
    for prim in mesh.primitives:
        blender_mesh.materials.append(manager.materials[prim.material])

    attributes = gltf_buffer.VertexBuffer(
        manager.base_dir, manager.gltf, mesh, manager.yup_to_zup)

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
