import pathlib
from typing import Any, List

import bpy
import mathutils  # pylint: disable=E0401
from progress_report import ProgressReport

from .. import gltftypes, gltf_buffer
from .import_manager import ImportManager
from .node import Node


class Skin:
    def __init__(self, base_dir: pathlib.Path, gltf: gltftypes.glTF, skin: gltftypes.Skin)->None:
        self.base_dir = base_dir
        self.gltf = gltf
        self.skin = skin
        self.inverse_matrices: Any = None

    def get_matrix(self, joint: int)->Any:
        if not self.inverse_matrices:
            self.inverse_matrices = gltf_buffer.get_array(
                self.base_dir, self.gltf, self.skin.inverseBindMatrices)
        m = self.inverse_matrices[joint]
        mat = mathutils.Matrix((
            (m.f00, m.f10, m.f20, m.f30),
            (m.f01, m.f11, m.f21, m.f31),
            (m.f02, m.f12, m.f22, m.f32),
            (m.f03, m.f13, m.f23, m.f33)
        ))
        # d = mat.decompose()
        return mat


def load_objects(context, progress: ProgressReport,
                 manager: ImportManager)->List[Node]:
    progress.enter_substeps(len(manager.gltf.nodes)+1, "Loading objects...")

    # collection
    view_layer = context.view_layer
    if view_layer.collections.active:
        collection = view_layer.collections.active.collection
    else:
        collection = context.scene.master_collection.new()
        view_layer.collections.link(collection)

    # setup
    nodes = [Node(i, gltf_node)
             for i, gltf_node in enumerate(manager.gltf.nodes)]

    # set parents
    for gltf_node, node in zip(manager.gltf.nodes, nodes):
        for child_index in gltf_node.children:
            child = nodes[child_index]
            node.children.append(child)
            child.parent = node
    if nodes[0].parent:
        raise Exception()

    progress.step()

    nodes[0].create_object(progress, collection, manager)

    # create armatures
    for skin in manager.gltf.skins:
        nodes[skin.skeleton].create_armature(
            context, collection, view_layer, skin)

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    progress.leave_substeps()
    return nodes
