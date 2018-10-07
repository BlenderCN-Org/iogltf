import pathlib
import json
from typing import List, Any, Optional, Tuple, Generator

import bpy
import mathutils  # pylint: disable=E0401
from bpy_extras.image_utils import load_image
from progress_report import ProgressReport

from .. import gltftypes, gltf_buffer
from . import blender_groupnode_io, gltf_pbr_node

from logging import getLogger  # pylint: disable=C0411
logger = getLogger(__name__)


def load_textures(progress: ProgressReport, base_dir: pathlib.Path,
                  gltf: gltftypes.glTF)->List[Any]:

    def create_texture(texture: gltftypes.Texture):
        image = gltf.images[texture.source]
        texture = load_image(image.uri, str(base_dir))
        progress.step()
        return texture

    progress.enter_substeps(len(gltf.textures), "Loading textures...")
    textures = [create_texture(texture) for texture in gltf.textures]
    progress.leave_substeps()
    return textures


def load_materials(progress: ProgressReport,
                   textures: List[Any], gltf: gltftypes.glTF)->List[Any]:

    def create_material(material: gltftypes.Material):
        blender_material = bpy.data.materials.new(material.name)
        blender_material['js'] = json.dumps(material.js, indent=2)

        blender_material.use_nodes = True
        tree = blender_material.node_tree

        tree.nodes.remove(tree.nodes['Principled BSDF'])

        getLogger('').disabled = True
        groups = blender_groupnode_io.import_groups(gltf_pbr_node.groups)
        getLogger('').disabled = False

        bsdf = tree.nodes.new('ShaderNodeGroup')
        bsdf.node_tree = groups['glTF Metallic Roughness']

        tree.links.new(
            bsdf.outputs['Shader'], tree.nodes['Material Output'].inputs['Surface'])

        def create_image_node(texture_index: int):
            # uv => tex
            image_node = tree.nodes.new(
                type='ShaderNodeTexImage')
            image_node.image = textures[texture_index]
            tree.links.new(
                tree.nodes.new('ShaderNodeTexCoord').outputs['UV'], image_node.inputs['Vector'])
            return image_node

        def bsdf_link_image(texture_index: int, input_name: str):
            texture = create_image_node(texture_index)
            tree.links.new(
                texture.outputs["Color"],
                bsdf.inputs[input_name])

        if material.normalTexture:
            bsdf_link_image(material.normalTexture.index, 'Normal')

        if material.occlusionTexture:
            bsdf_link_image(material.occlusionTexture.index, 'Occlusion')

        if material.emissiveTexture:
            bsdf_link_image(material.emissiveTexture.index, 'Emissive')

        pbr = material.pbrMetallicRoughness
        if pbr:
            if pbr.baseColorTexture and pbr.baseColorFactor:
                # mix
                mix = tree.nodes.new(type='ShaderNodeMixRGB')
                mix.blend_type = 'MULTIPLY'
                mix.inputs[2].default_value = pbr.baseColorFactor

            elif pbr.baseColorTexture:
                bsdf_link_image(pbr.baseColorTexture.index, 'BaseColor')
            else:
                # factor
                pass

            if pbr.metallicRoughnessTexture:
                bsdf_link_image(
                    pbr.metallicRoughnessTexture.index, 'MetallicRoughness')

        progress.step()
        return blender_material

    progress.enter_substeps(len(gltf.textures), "Loading materials...")
    materials = [create_material(material) for material in gltf.materials]
    progress.leave_substeps()
    return materials


def load_meshes(progress: ProgressReport, base_dir: pathlib.Path,
                materials: List[Any], gltf: gltftypes.glTF)->List[Any]:

    def create_mesh(mesh: gltftypes.Mesh):
        blender_mesh = bpy.data.meshes.new(mesh.name)
        for prim in mesh.primitives:
            blender_mesh.materials.append(materials[prim.material])

        vertices = gltf_buffer.VertexBuffer(base_dir, gltf, mesh)

        blender_mesh.vertices.add(len(vertices.pos)/3)
        blender_mesh.vertices.foreach_set(
            "co", vertices.pos)
        blender_mesh.vertices.foreach_set(
            "normal", vertices.nom)

        blender_mesh.loops.add(len(vertices.indices))
        blender_mesh.loops.foreach_set("vertex_index", vertices.indices)

        triangle_count = int(len(vertices.indices) / 3)
        blender_mesh.polygons.add(triangle_count)
        starts = [i * 3 for i in range(triangle_count)]
        blender_mesh.polygons.foreach_set("loop_start", starts)
        total = [3 for _ in range(triangle_count)]
        blender_mesh.polygons.foreach_set("loop_total", total)

        blen_uvs = blender_mesh.uv_layers.new()
        for blen_poly in blender_mesh.polygons:
            blen_poly.use_smooth = True
            for lidx in blen_poly.loop_indices:
                index = vertices.indices[lidx]
                # vertex uv to face uv
                uv = vertices.uv[index]
                blen_uvs.data[lidx].uv = (
                    uv.x, uv.y)  # vertical flip uv

        # *Very* important to not remove lnors here!
        blender_mesh.validate(clean_customdata=False)
        blender_mesh.update()

        progress.step()
        return blender_mesh

    progress.enter_substeps(len(gltf.meshes), "Loading meshes...")
    meshes = [create_mesh(mesh) for mesh in gltf.meshes]
    progress.leave_substeps()
    return meshes


class Node:
    def __init__(self, index: int, gltf_node: gltftypes.Node, is_skin: bool)->None:
        self.index = index
        self.gltf_node = gltf_node
        self.is_skin = is_skin
        self.parent: Optional[Node] = None
        self.children: List[Node] = []
        self.blender_object: Any = None

    def __str__(self)->str:
        return f'{self.index}'

    def traverse(self)->Generator['Node', None, None]:
        yield self
        for child in self.children:
            for x in child.traverse():
                yield x


def load_objects(progress: ProgressReport,
                 meshes: List[Any], gltf: gltftypes.glTF)->List[Any]:
    progress.enter_substeps(len(gltf.nodes)+1, "Loading objects...")

    # setup
    def is_skin(i: int)->bool:
        for skin in gltf.skins:
            for joint in skin.joints:
                if joint == i:
                    return True
        return False
    nodes = [Node(i, gltf_node, is_skin(i))
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

    progress.leave_substeps()
    return [node.blender_object for node in nodes]
