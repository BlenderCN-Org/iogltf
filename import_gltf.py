import json
import pathlib
import ctypes
from typing import Set, Dict

import bpy
from progress_report import ProgressReport  # , ProgressReportSubstep
from bpy_extras.image_utils import load_image

from . import gltftypes


class Float2(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


class Float3(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]


buffer_map: Dict[str, bytes] = {}


def get_view_bytes(base: pathlib.Path, gltf: gltftypes.glTF, view_index: int)->bytes:
    view = gltf.bufferViews[view_index]
    buffer = gltf.buffers[view.buffer]
    if buffer.uri:
        if buffer.uri in buffer_map:
            return buffer_map[buffer.uri][view.byteOffset:view.byteOffset+view.byteLength]
        else:
            path = base / buffer.uri
            with path.open('rb') as f:
                data = f.read()
                buffer_map[buffer.uri] = data
                return data[view.byteOffset:view.byteOffset+view.byteLength]
    else:
        raise Exception('glb not implemented')


def get_accessor_type_to_count(accessor_type: gltftypes.Accessor_type)->int:
    if accessor_type == gltftypes.Accessor_type.SCALAR:
        return 1
    if accessor_type == gltftypes.Accessor_type.VEC2:
        return 2
    if accessor_type == gltftypes.Accessor_type.VEC3:
        return 3
    if accessor_type == gltftypes.Accessor_type.VEC4:
        return 4
    if accessor_type == gltftypes.Accessor_type.MAT2:
        return 4
    if accessor_type == gltftypes.Accessor_type.MAT3:
        return 9
    if accessor_type == gltftypes.Accessor_type.MAT4:
        return 16


def get_accessor_component_type_to_len(component_type: gltftypes.Accessor_componentType)->int:
    if component_type == gltftypes.Accessor_componentType.BYTE:
        return 1
    if component_type == gltftypes.Accessor_componentType.SHORT:
        return 2
    if component_type == gltftypes.Accessor_componentType.UNSIGNED_BYTE:
        return 1
    if component_type == gltftypes.Accessor_componentType.UNSIGNED_SHORT:
        return 2
    if component_type == gltftypes.Accessor_componentType.UNSIGNED_INT:
        return 4
    if component_type == gltftypes.Accessor_componentType.FLOAT:
        return 4


def get_accessor_byteslen(accessor: gltftypes.Accessor)->int:
    return (accessor.count
            * get_accessor_type_to_count(accessor.type)
            * get_accessor_component_type_to_len(accessor.componentType))


def get_array(base: pathlib.Path, gltf: gltftypes.glTF, accessor_index: int, array_type):
    accessor = gltf.accessors[accessor_index]
    accessor_byte_len = get_accessor_byteslen(accessor)
    segment = get_view_bytes(base, gltf, accessor.bufferView)[
        accessor.byteOffset:accessor.byteOffset+accessor_byte_len]
    return (array_type * accessor.count).from_buffer_copy(segment)


def get_indices(base: pathlib.Path, gltf: gltftypes.glTF, accessor_index: int):
    accessor = gltf.accessors[accessor_index]
    accessor_byte_len = get_accessor_byteslen(accessor)
    segment = get_view_bytes(base, gltf, accessor.bufferView)[
        accessor.byteOffset:accessor.byteOffset+accessor_byte_len]
    if (accessor.componentType == gltftypes.Accessor_componentType.SHORT
            or accessor.componentType == gltftypes.Accessor_componentType.UNSIGNED_SHORT):
        return (ctypes.c_ushort * accessor.count).from_buffer_copy(segment)
    elif accessor.componentType == gltftypes.Accessor_componentType.UNSIGNED_INT:
        return (ctypes.c_uint * accessor.count).from_buffer_copy(segment)


class Submesh:
    def __init__(self, path: pathlib.Path, gltf: gltftypes.glTF, prim: gltftypes.MeshPrimitive)->None:
        pos_index = prim.attributes['POSITION']
        self.pos = get_array(path, gltf, pos_index, Float3)

        self.nom = None
        if 'NORMAL' in prim.attributes:
            nom_index = prim.attributes['NORMAL']
            self.nom = get_array(path, gltf, nom_index, Float3)
            if len(self.nom) != len(self.pos):
                raise Exception('nom len is not equals to pos')

        self.um = None
        if 'TEXCOORD_0' in prim.attributes:
            uv_index = prim.attributes['TEXCOORD_0']
            self.uv = get_array(path, gltf, uv_index, Float2)
            if len(self.uv) != len(self.pos):
                raise Exception('uv len is not equals to pos')

        self.indices = get_indices(path, gltf, prim.indices)


class VertexBuffer:
    def __init__(self, path: pathlib.Path, gltf: gltftypes.glTF, mesh: gltftypes.Mesh)->None:
        submeshes = [Submesh(path, gltf, prim) for prim in mesh.primitives]

        # merge submesh
        pos_count = sum((len(x.pos) for x in submeshes), 0)
        self.pos = (ctypes.c_float * (pos_count * 3))()
        self.nom = (ctypes.c_float * (pos_count * 3))()
        self.uv = (Float2 * (pos_count))()

        index_count = sum((len(x.indices) for x in submeshes), 0)
        self.indices = (ctypes.c_int * index_count)()

        pos_index = 0
        nom_index = 0
        uv_index = 0
        index = 0
        for submesh in submeshes:
            for v in submesh.pos:
                self.pos[pos_index] = v.x
                pos_index += 1
                self.pos[pos_index] = -v.z
                pos_index += 1
                self.pos[pos_index] = v.y
                pos_index += 1
            for n in submesh.nom:
                self.nom[nom_index] = n.x
                nom_index += 1
                self.nom[nom_index] = -n.z
                nom_index += 1
                self.nom[nom_index] = n.y
                nom_index += 1
            for uv in submesh.uv:
                self.uv[uv_index].x = uv.x
                self.uv[uv_index].y = uv.y
                uv_index += 1
            for i in submesh.indices:
                self.indices[index] = i
                index += 1


def load(context, filepath: str, global_matrix)->Set[str]:
    path = pathlib.Path(filepath)
    base_dir = path.parent
    if not path.exists():
        return {'CANCELLED'}

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(1, "Importing GLTF %r..." % filepath)

        progress.enter_substeps(2, "Parsing GLTF file...")
        with path.open() as f:
            gltf = gltftypes.from_json(json.load(f))

        progress.step("Done, loading images:%i..." % len(gltf.images))

        def create_texture(texture: gltftypes.Texture):
            image = gltf.images[texture.source]
            texture = load_image(image.uri, str(base_dir))
            return texture
        textures = [create_texture(texture) for texture in gltf.textures]
        print(textures)

        progress.step("Done, loading materials:%i..." % len(gltf.materials))

        def create_material(material: gltftypes.Material):
            blender_material = bpy.data.materials.new(material.name)
            blender_material['js'] = json.dumps(material.js, indent=2)

            blender_material.use_nodes = True
            tree = blender_material.node_tree
            for x in tree.nodes:
                print(x)

            pbr = material.pbrMetallicRoughness
            if pbr:
                bsdf = tree.nodes['Principled BSDF']
                def bsdf_link_image(texture_index: int, input: str):
                    texture = tree.nodes.new(
                        type='ShaderNodeTexImage')
                    texture.image = textures[texture_index]
                    tree.links.new(
                        texture.outputs["Color"], 
                        bsdf.inputs[input])
                    # uv => tex
                    tex_coord = tree.nodes.new('ShaderNodeTexCoord')
                    tree.links.new(
                        tex_coord.outputs['UV'],  texture.inputs['Vector'])

                if pbr.baseColorTexture and pbr.baseColorFactor:
                    # mix
                    mix = tree.nodes.new(type = 'ShaderNodeMixRGB')
                    mix.blend_type = 'MULTIPLY'
                    mix.inputs[2].default_value = pbr.baseColorFactor

                elif pbr.baseColorTexture:
                    bsdf_link_image(pbr.baseColorTexture.index, 'Base Color')
                else:
                    # factor
                    pass

                if pbr.metallicRoughnessTexture:
                    bsdf_link_image(pbr.metallicRoughnessTexture.index, 'Metallic')
                    bsdf_link_image(pbr.metallicRoughnessTexture.index, 'Roughness')

            return blender_material
        materials = [create_material(material) for material in gltf.materials]
        print(materials)

        progress.step("Done, building geometries (mesh:%i) ..." %
                      (len(gltf.meshes)))

        def create_mesh(mesh: gltftypes.Mesh):
            blender_mesh = bpy.data.meshes.new(mesh.name)
            for prim in mesh.primitives:
                blender_mesh.materials.append(materials[prim.material])

            vertices = VertexBuffer(base_dir, gltf, mesh)

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
                        uv.x, 1.0 - uv.y)  # vertical flip uv
            print(blen_uvs)

            # *Very* important to not remove lnors here!
            blender_mesh.validate(clean_customdata=False)
            blender_mesh.update()

            return blender_mesh
        meshes = [create_mesh(mesh) for mesh in gltf.meshes]
        print(meshes)

        progress.step("Done, building objects (object:%i) ..." %
                      (len(gltf.nodes)))

        def create_object(node: gltftypes.Node):
            if node.mesh != -1:
                blender_object = bpy.data.objects.new(
                    node.name, meshes[node.mesh])
            else:
                blender_object = bpy.data.objects.new(node.name, None)
            return blender_object
        objects = [create_object(node) for node in gltf.nodes]
        print(objects)

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
            obj.matrix_world = global_matrix

        context.scene.update()

        return {'FINISHED'}
