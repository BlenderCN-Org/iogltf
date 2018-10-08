from typing import Optional, List, Any, Generator
import json

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

    def create_object(self, progress: ProgressReport,
                      collection, meshes: List[Any], mod_v, mod_q)->None:
        name = self.gltf_node.name
        if not name:
            name = '_%03d' % self.index

        # create object
        if self.gltf_node.mesh != -1:
            self.blender_object = bpy.data.objects.new(
                name, meshes[self.gltf_node.mesh])
        else:
            # empty
            self.blender_object = bpy.data.objects.new(name, None)
            self.blender_object.empty_display_size = 0.1
            #self.blender_object.empty_draw_type = 'PLAIN_AXES'
        collection.objects.link(self.blender_object)
        self.blender_object.select_set("SELECT")

        self.blender_object['js'] = json.dumps(self.gltf_node.js, indent=2)

        # parent
        if self.parent:
            self.blender_object.parent = self.parent.blender_object

        if self.gltf_node.translation:
            self.blender_object.location = mod_v(self.gltf_node.translation)

        if self.gltf_node.rotation:
            r = self.gltf_node.rotation
            q = mathutils.Quaternion((r[3], r[0], r[1], r[2]))
            self.blender_object.rotation_mode = 'QUATERNION'
            self.blender_object.rotation_quaternion = mod_q(q)

        if self.gltf_node.scale:
            s = self.gltf_node.scale
            self.blender_object.scale = (s[0], s[2], s[1])

        if self.gltf_node.matrix:
            m = self.gltf_node.matrix
            matrix = mathutils.Matrix((
                (m[0], m[4], m[8], m[12]),
                (m[1], m[5], m[9], m[13]),
                (m[2], m[6], m[10], m[14]),
                (m[3], m[7], m[11], m[15])
            ))
            t, q, s = matrix.decompose()
            self.blender_object.location = mod_v(t)
            self.blender_object.rotation_mode = 'QUATERNION'
            self.blender_object.rotation_quaternion = mod_q(q)
            self.blender_object.scale = (s[0], s[2], s[1])

        progress.step()

        for child in self.children:
            child.create_object(progress, collection, meshes, mod_v, mod_q)

    # create armature
    def create_armature(self, collection, view_layer)->None:
        if not self.skin:
            return
        skin = self.skin

        if not self.blender_object:
            return
        blender_object = self.blender_object

        #parent_blender_object = node.parent.blender_object if node.parent else None

        node_name = self.gltf_node.name
        if not node_name:
            node_name = '_%03d' % self.index

        skin_name = skin.name
        if skin_name:
            skin_name = 'armature' + node_name

        armature = None
        parent_bone = None
        if self.parent and self.parent.skin == skin:
            armature = self.parent.blender_armature.data
            self.blender_armature = self.parent.blender_armature
            parent_bone = self.parent.blender_bone
        else:
            # new armature
            armature = bpy.data.armatures.new(skin_name)
            self.blender_armature = bpy.data.objects.new(skin_name, armature)
            collection.objects.link(self.blender_armature)

            # select and edit mode
            self.blender_armature.select_set("SELECT")
            view_layer.objects.active = self.blender_armature
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        # create bone
        self.blender_bone = armature.edit_bones.new(node_name)
        #parent_position = mathutils.Vector((0, 0, 0))
        if parent_bone:
            self.blender_bone.parent = parent_bone
            self.blender_bone.use_connect = True
            #parent_position = parent_blender_object.matrix_world.to_translation()
        self.blender_bone.head = blender_object.matrix_world.to_translation()
        if not self.children:
            self.blender_bone.tail = self.blender_bone.head + \
                (self.blender_bone.head - self.parent.blender_bone.head)


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

    # setup from root to descendants
    def mod_v(v):
        # return (v[0], v[1], v[2])
        return v

    def mod_q(q):
        # return mathutils.Quaternion(mod_v(q.axis), q.angle)
        return q
    nodes[0].create_object(progress, collection, meshes, mod_v, mod_q)

    # build armature
    nodes[0].create_armature(collection, view_layer)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    progress.leave_substeps()
    return [node.blender_object for node in nodes]
