from typing import Optional, List, Any, Generator

import bpy
import mathutils  # pylint: disable=E0401
from progress_report import ProgressReport

from .. import gltftypes


class Node:
    def __init__(self, index: int, gltf_node: gltftypes.Node, skins: List[gltftypes.Skin])->None:
        self.index = index
        self.gltf_node = gltf_node
        self.parent: Optional[Node] = None
        self.children: List[Node] = []
        self.blender_object: Any = None

        self.skin: Optional[gltftypes.Skin] = None
        if len(skins) > 1:
            raise Exception('Multiple skin')
        elif len(skins) == 1:
            self.skin = skins[0]
        self.blender_armature: Any = None
        self.blender_bone: Any = None

    def __str__(self)->str:
        return f'{self.index}'

    def traverse(self)->Generator['Node', None, None]:
        yield self
        for child in self.children:
            for x in child.traverse():
                yield x


def load_objects(context, progress: ProgressReport,
                 meshes: List[Any], gltf: gltftypes.glTF)->List[Any]:
    progress.enter_substeps(len(gltf.nodes)+1, "Loading objects...")

    # collection
    view_layer = context.view_layer
    if view_layer.collections.active:
        collection = view_layer.collections.active.collection
    else:
        collection = context.scene.master_collection.new()
        view_layer.collections.link(collection)

    # setup
    def get_skins(i: int)->Generator[gltftypes.Skin, None, None]:
        for skin in gltf.skins:
            for joint in skin.joints:
                if joint == i:
                    yield skin
    nodes = [Node(i, gltf_node, [skin for skin in get_skins(i)])
             for i, gltf_node in enumerate(gltf.nodes)]

    # set parents
    for gltf_node, node in zip(gltf.nodes, nodes):
        for child_index in gltf_node.children:
            child = nodes[child_index]
            node.children.append(child)
            child.parent = node
    if nodes[0].parent:
        raise Exception()

    progress.step()

    def mod_v(v):
        return (v[0], -v[2], v[1])

    def mod_q(q):
        return mathutils.Quaternion(mod_v(q.axis), q.angle)

    # setup from root to descendants
    def create_object(node: Node):
        name = node.gltf_node.name
        if not name:
            name = '_%03d' % node.index

        # create object
        if node.gltf_node.mesh != -1:
            node.blender_object = bpy.data.objects.new(
                name, meshes[node.gltf_node.mesh])
        else:
            node.blender_object = bpy.data.objects.new(name, None)
        collection.objects.link(node.blender_object)
        node.blender_object.select_set("SELECT")

        # parent
        if node.parent:
            node.blender_object.parent = node.parent.blender_object

        if node.gltf_node.translation:
            node.blender_object.location = mod_v(node.gltf_node.translation)

        if node.gltf_node.rotation:
            r = node.gltf_node.rotation
            q = mathutils.Quaternion((r[3], r[0], r[1], r[2]))
            node.blender_object.rotation_quaternion = mod_q(q)

        if node.gltf_node.scale:
            s = node.gltf_node.scale
            node.blender_object.scale = (s[0], s[2], s[1])

        if node.gltf_node.matrix:
            m = node.gltf_node.matrix
            matrix = mathutils.Matrix((
                (m[0], m[4], m[8], m[12]),
                (m[1], m[5], m[9], m[13]),
                (m[2], m[6], m[10], m[14]),
                (m[3], m[7], m[11], m[15])
            ))
            t, q, s = matrix.decompose()
            node.blender_object.location = mod_v(t)
            node.blender_object.rotation_quaternion = mod_q(q)
            node.blender_object.scale = (s[0], s[2], s[1])

        progress.step()
    for node in nodes[0].traverse():
        create_object(node)

    # create armature
    def create_armature(node: Node):
        if not node.skin:
            return

        node_name = node.gltf_node.name
        if not node_name:
            node_name = '_%03d' % node.index

        skin_name = node.skin.name
        if skin_name:
            skin_name = 'armature' + node_name

        armature = None
        parent_bone = None
        if node.parent and node.parent.skin == node.skin:
            armature = node.parent.blender_armature.data
            node.blender_armature = node.parent.blender_armature
            parent_bone = node.parent.blender_bone
        else:
            # new armature
            armature = bpy.data.armatures.new(skin_name)
            node.blender_armature = bpy.data.objects.new(skin_name, armature)
            collection.objects.link(node.blender_armature)

            # select and edit mode
            node.blender_armature.select_set("SELECT")
            view_layer.objects.active = node.blender_armature
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        # create bone
        node.blender_bone = armature.edit_bones.new(node_name)
        if parent_bone:
            node.blender_bone.parent = parent_bone
        node.blender_bone.head = (0, 0, 1)

    for node in nodes[0].traverse():
        create_armature(node)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    progress.leave_substeps()
    return [node.blender_object for node in nodes]

print('yxxx')
