import json
import pathlib
import ctypes
from typing import Set, Dict

import bpy
import mathutils
from progress_report import ProgressReport  # , ProgressReportSubstep

from . import gltftypes
from . import gltf_pbr_node
from . import blender_groupnode_io
from . import blender_io
from . import gltf_buffer


from logging import getLogger, CRITICAL, DEBUG  # pylint: disable=C0411
logger = getLogger(__name__)



def load(context, filepath: str, global_matrix)->Set[str]:
    path = pathlib.Path(filepath)
    base_dir = path.parent
    if not path.exists():
        return {'CANCELLED'}

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(10, "Importing GLTF %r..." % filepath)

        progress.step("Parsing GLTF file...")
        with path.open() as f:
            gltf = gltftypes.from_json(json.load(f))

        textures = blender_io.load_textures(progress, base_dir, gltf)

        progress.enter_substeps(len(gltf.materials), "Loading materials...")
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
                    tree.nodes.new('ShaderNodeTexCoord').outputs['UV'],  image_node.inputs['Vector'])
                return image_node

            def bsdf_link_image(texture_index: int, input: str):
                texture = create_image_node(texture_index)
                tree.links.new(
                    texture.outputs["Color"],
                    bsdf.inputs[input])

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

            return blender_material
        materials = [create_material(material) for material in gltf.materials]
        print(materials)

        progress.step("Done, building geometries (mesh:%i) ..." %
                      (len(gltf.meshes)))

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
            print(blen_uvs)

            # *Very* important to not remove lnors here!
            blender_mesh.validate(clean_customdata=False)
            blender_mesh.update()

            return blender_mesh
        meshes = [create_mesh(mesh) for mesh in gltf.meshes]
        print(meshes)

        progress.step("Done, building objects (object:%i) ..." %
                      (len(gltf.nodes)))

        def create_object(i: int, node: gltftypes.Node):
            name = node.name
            if not name:
                name = '_%03d' % i

            if node.mesh != -1:
                blender_object = bpy.data.objects.new(
                    name, meshes[node.mesh])
            else:
                blender_object = bpy.data.objects.new(name, None)

            return blender_object

        objects = [create_object(i, node) for i, node in enumerate(gltf.nodes)]
        print(objects)

        for blender_object, node in zip(objects, gltf.nodes):
            if node.children:
                for child in node.children:
                    objects[child].parent = blender_object

        def mod_v(v):
            return (v[0], -v[2], v[1])
        def mod_q(q):
            return mathutils.Quaternion(mod_v(q.axis), q.angle)
        for blender_object, node in zip(objects, gltf.nodes):
            if node.translation:
                blender_object.location = mod_v(node.translation)

            if node.rotation:
                r = node.rotation
                q = mathutils.Quaternion((r[3], r[0], r[1], r[2]))
                blender_object.rotation_quaternion = mod_q(q)

            if node.scale:
                s = node.scale
                blender_object.scale = (s[0], s[2], s[1])

            if node.matrix:
                m = node.matrix
                matrix = mathutils.Matrix((
                    (m[0], m[4], m[8], m[12]),
                    (m[1], m[5], m[9], m[13]),
                    (m[2], m[6], m[10], m[14]),
                    (m[3], m[7], m[11], m[15])
                ))
                t, q, s = matrix.decompose()
                blender_object.location = mod_v(t)
                blender_object.rotation_quaternion = mod_q(q)
                blender_object.scale = (s[0], s[2], s[1])

        view_layer = context.view_layer
        if view_layer.collections.active:
            collection = view_layer.collections.active.collection
        else:
            collection = context.scene.master_collection.new()
            view_layer.collections.link(collection)

        # Create new obj
        for obj in objects:
            collection.objects.link(obj)
            obj.select_set('SELECT')

            # we could apply this anywhere before scaling.
            #obj.matrix_world = global_matrix

        context.scene.update()

        return {'FINISHED'}
