import pathlib
import json
from typing import List, Any, Optional, Tuple, Generator

import bpy
import mathutils  # pylint: disable=E0401
from bpy_extras.image_utils import load_image
from progress_report import ProgressReport

from .. import gltftypes, gltf_buffer
from . import blender_groupnode_io, gltf_pbr_node
from .node_io import *  # pylint: disable=W0401

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
                materials: List[Any], gltf: gltftypes.glTF
                )->List[Tuple[bpy.types.Mesh, gltf_buffer.VertexBuffer]]:

    def create_mesh(mesh: gltftypes.Mesh):
        blender_mesh = bpy.data.meshes.new(mesh.name)
        for prim in mesh.primitives:
            blender_mesh.materials.append(materials[prim.material])

        attributes = gltf_buffer.VertexBuffer(base_dir, gltf, mesh)

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

    progress.enter_substeps(len(gltf.meshes), "Loading meshes...")
    meshes = [create_mesh(mesh) for mesh in gltf.meshes]
    progress.leave_substeps()
    return meshes
