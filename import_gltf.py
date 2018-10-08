import json
import pathlib
from typing import Set, List
from progress_report import ProgressReport  # , ProgressReportSubstep

import bpy

from . import gltftypes, blender_io

from logging import getLogger  # pylint: disable=C0411
logger = getLogger(__name__)


def setup_skinning(blender_object: bpy.types.Object,
                   joints, weights, bone_names: List[str],
                   armature_object: bpy.types.Object)->None:
    # create vertex groups
    for bone_name in bone_names:
        blender_object.vertex_groups.new(
            name=bone_name)

    idx_already_done: Set[int] = set()

    # each face
    for poly in blender_object.data.polygons:
        # face vertex index
        for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vert_idx = blender_object.data.loops[loop_idx].vertex_index

            if vert_idx in idx_already_done:
                continue
            idx_already_done.add(vert_idx)

            cpt = 0
            for joint_idx in joints[vert_idx]:
                weight_val = weights[vert_idx][cpt]
                if weight_val != 0.0:
                    # It can be a problem to assign weights of 0
                    # for bone index 0, if there is always 4 indices in joint_ tuple
                    bone_name = bone_names[joint_idx]
                    group = blender_object.vertex_groups[bone_name]
                    group.add([vert_idx], weight_val, 'REPLACE')
                cpt += 1

    # select
    #for obj_sel in bpy.context.scene.objects:
    #    obj_sel.select = False
    #blender_object.select = True
    #bpy.context.scene.objects.active = blender_object

    modifier = blender_object.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature_object


def load(context, filepath: str,
         global_matrix  # pylint: disable=W0613
         )->Set[str]:
    path = pathlib.Path(filepath)
    base_dir = path.parent
    if not path.exists():
        return {'CANCELLED'}

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(5, "Importing GLTF %r..." % path.name)

        with path.open() as f:
            gltf = gltftypes.from_json(json.load(f))

        textures = blender_io.load_textures(progress, base_dir, gltf)

        materials = blender_io.load_materials(progress, textures, gltf)

        meshes = blender_io.load_meshes(progress, base_dir, materials, gltf)

        nodes = blender_io.load_objects(context, progress, base_dir,
                                        [mesh for mesh, _ in meshes], gltf)

        # skinning
        for node in nodes:
            if node.gltf_node.mesh != -1 and node.gltf_node.skin != -1:
                _, attributes = meshes[node.gltf_node.mesh]
                skin = gltf.skins[node.gltf_node.skin]
                bone_names = [nodes[joint].bone_name for joint in skin.joints]
                setup_skinning(node.blender_object, attributes.joints,
                               attributes.weights, bone_names,
                               nodes[skin.skeleton].blender_armature)

        context.scene.update()

        progress.leave_substeps("Finished")
        return {'FINISHED'}
