import json
import pathlib
import ctypes
from typing import Set, Dict

import bpy
import mathutils
from progress_report import ProgressReport  # , ProgressReportSubstep
from bpy_extras.image_utils import load_image

from . import gltftypes
from . import gltf_pbr_node
from . import blender_groupnode_io


from logging import getLogger, CRITICAL, DEBUG  # pylint: disable=C0411
logger = getLogger(__name__)


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


class VertexBuffer:
    def __init__(self, path: pathlib.Path, gltf: gltftypes.glTF, mesh: gltftypes.Mesh)->None:
        # check shared attributes
        attributes = {}
        shared = True
        for prim in mesh.primitives:
            print(prim.attributes)
            if not attributes:
                attributes = prim.attributes
            else:
                if attributes != prim.attributes:
                    shared = False
                    break
        print(shared)

        #submeshes = [Submesh(path, gltf, prim) for prim in mesh.primitives]

        # merge submesh
        def position_count(prim):
            accessor_index = prim.attributes['POSITION']
            return gltf.accessors[accessor_index].count
        pos_count = sum((position_count(prim) for prim in mesh.primitives), 0)
        self.pos = (ctypes.c_float * (pos_count * 3))()
        self.nom = (ctypes.c_float * (pos_count * 3))()
        self.uv = (Float2 * (pos_count))()

        def index_count(prim):
            return gltf.accessors[prim.indices].count
        index_count = sum((index_count(prim) for prim in mesh.primitives), 0)
        self.indices = (ctypes.c_int * index_count)()

        pos_index = 0
        nom_index = 0
        uv_index = 0
        indices_index = 0
        offset = 0
        for prim in mesh.primitives:
            #
            # attributes
            #
            pos = get_array(path, gltf, prim.attributes['POSITION'], Float3)
            if 'NORMAL' in prim.attributes:
                nom = get_array(path, gltf, prim.attributes['NORMAL'], Float3)
                if len(nom) != len(pos):
                    raise Exception("len(nom) different from len(pos)")
            if 'TEXCOORD_0' in prim.attributes:
                uv = get_array(path, gltf, prim.attributes['TEXCOORD_0'], Float2)
                if len(uv) != len(pos):
                    raise Exception("len(uv) different from len(pos)")
            for i in range(len(pos)):
                self.pos[pos_index] = pos[i].x
                pos_index+=1
                self.pos[pos_index] = -pos[i].z
                pos_index+=1
                self.pos[pos_index] = pos[i].y
                pos_index+=1

                if nom:
                    self.nom[nom_index] = nom[i].x
                    nom_index+=1
                    self.nom[nom_index] = -nom[i].z
                    nom_index+=1
                    self.nom[nom_index] = nom[i].y
                    nom_index+=1

                if uv:
                    xy = uv[i]
                    xy.y = 1.0 - xy.y
                    self.uv[uv_index] = xy
                    uv_index+=1

            #
            # indices
            #
            indices = get_indices(path, gltf, prim.indices)
            for i in indices:
                self.indices[indices_index] = offset + i
                indices_index += 1
            offset += len(pos)


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
