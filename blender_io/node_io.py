from typing import Optional, List, Any
import json
import pathlib
from contextlib import contextmanager

import bpy
import mathutils  # pylint: disable=E0401
from progress_report import ProgressReport

from .. import gltftypes, gltf_buffer



@contextmanager
def tmp_mode(obj, tmp: str):
    mode = obj.rotation_mode
    obj.rotation_mode = tmp
    try:
        yield
    finally:
        obj.rotation_mode = mode


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


class Node:
    def __init__(self, index: int, gltf_node: gltftypes.Node)->None:
        self.index = index
        self.gltf_node = gltf_node
        self.parent: Optional[Node] = None
        self.children: List[Node] = []
        self.blender_object: bpy.types.Object = None
        self.blender_armature: bpy.types.Object = None
        self.blender_bone: bpy.types.Bone = None
        self.bone_name: str = ''

        self.name = self.gltf_node.name
        if not self.name:
            self.name = '_%03d' % self.index

    def __str__(self)->str:
        return f'{self.index}'

    def create_object(self, progress: ProgressReport,
                      collection, meshes: List[Any], mod_v, mod_q)->None:
        # create object
        if self.gltf_node.mesh != -1:
            self.blender_object = bpy.data.objects.new(
                self.name, meshes[self.gltf_node.mesh])
        else:
            # empty
            self.blender_object = bpy.data.objects.new(self.name, None)
            self.blender_object.empty_display_size = 0.1
            # self.blender_object.empty_draw_type = 'PLAIN_AXES'
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
            with tmp_mode(self.blender_object, 'QUATERNION'):
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
            with tmp_mode(self.blender_object, 'QUATERNION'):
                self.blender_object.rotation_quaternion = mod_q(q)
            self.blender_object.scale = (s[0], s[2], s[1])

        progress.step()

        for child in self.children:
            child.create_object(progress, collection, meshes, mod_v, mod_q)

    # create armature
    def create_armature(self, context, collection, view_layer,
                        skin: gltftypes.Skin)->bpy.types.Object:
        skin_name = skin.name
        if skin_name:
            skin_name = 'armature' + self.name

        armature = bpy.data.armatures.new(skin_name)
        self.blender_armature = bpy.data.objects.new(
            skin_name, armature)
        collection.objects.link(self.blender_armature)
        self.blender_armature.show_in_front = True
        self.blender_armature.parent = self.blender_object.parent

        # select
        self.blender_armature.select_set("SELECT")
        view_layer.objects.active = self.blender_armature
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # set identity matrix_world to armature
        m = mathutils.Matrix()
        m.identity()
        self.blender_armature.matrix_world = m
        context.scene.update()  # recalc matrix_world

        # edit mode
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        self.create_bone(skin, armature, None, False)

    def create_bone(self, skin: gltftypes.Skin, armature: bpy.types.Armature,
                    parent_bone: bpy.types.Bone, is_connect: bool)->None:

        self.blender_bone = armature.edit_bones.new(self.name)
        self.bone_name = self.blender_bone.name
        self.blender_bone.use_connect = is_connect
        self.blender_bone.parent = parent_bone

        object_pos = self.blender_object.matrix_world.to_translation()
        self.blender_bone.head = object_pos

        if not self.children:
            if parent_bone:
                self.blender_bone.tail = self.blender_bone.head + \
                    (self.blender_bone.head - parent_bone.head)
        else:
            def get_child_is_connect(child_pos)->bool:
                if len(self.children) == 1:
                    return True

                parent_head = mathutils.Vector((0, 0, 0))
                if parent_bone:
                    parent_head = parent_bone.head
                parent_dir = (self.blender_bone.head -
                              parent_head).normalized()
                child_dir = (
                    child_pos - self.blender_object.matrix_world.to_translation()).normalized()
                dot = parent_dir.dot(child_dir)
                # print(parent_dir, child_dir, dot)
                return dot > 0.8

            for child in self.children:
                child_is_connect = get_child_is_connect(
                    child.blender_object.matrix_world.to_translation())
                child.create_bone(
                    skin, armature, self.blender_bone, child_is_connect)


def load_objects(context, progress: ProgressReport, base_dir: pathlib.Path,
                 meshes: List[Any], gltf: gltftypes.glTF)->List[Node]:
    progress.enter_substeps(len(gltf.nodes)+1, "Loading objects...")

    # collection
    view_layer = context.view_layer
    if view_layer.collections.active:
        collection = view_layer.collections.active.collection
    else:
        collection = context.scene.master_collection.new()
        view_layer.collections.link(collection)

    # setup
    nodes = [Node(i, gltf_node) for i, gltf_node in enumerate(gltf.nodes)]

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

    # create armatures
    for skin in gltf.skins:
        nodes[skin.skeleton].create_armature(
            context, collection, view_layer, skin)

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    progress.leave_substeps()
    return nodes
