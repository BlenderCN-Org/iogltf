import json
import pathlib
import ctypes
from typing import Set, Dict

import bpy
from progress_report import ProgressReport, ProgressReportSubstep
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils

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


class VertexBuffer:
    def __init__(self, path: pathlib.Path, gltf: gltftypes.glTF, mesh: gltftypes.Mesh):
        self.pos = []
        self.nom = []
        self.uv = []
        self.indices = []
        self.materials = []
        for prim in mesh.primitives:
            if 'POSITION' in prim.attributes:
                pos_index = prim.attributes['POSITION']
                pos = get_array(path, gltf, pos_index, Float3)
                self.pos.append(pos)
            if 'NORMAL' in prim.attributes:
                nom_index = prim.attributes['NORMAL']
                nom = get_array(path, gltf, nom_index, Float3)
                self.nom.append(nom)
            if 'TEXCOORD_0' in prim.attributes:
                uv_index = prim.attributes['TEXCOORD_0']
                uv = get_array(path, gltf, uv_index, Float2)
                self.uv.append(uv)
            '''
            if 'TANGENT' in prim.attributes:
                tan_index = prim.attributes['TANGENT']
                tan = get_array(gltf, tan_index, Float4)
            '''

            indices = get_indices(path, gltf, prim.indices)
            self.indices.append(indices)

        # integrate meshes

    def get_vertex_count(self):
        count = 0
        for pos in self.pos:
            count += len(pos)
        return count

    def iter_positions(self):
        for pos in self.pos:
            for v in pos:
                yield v.x
                yield v.y
                yield v.z

    def iter_uv(self):
        for i in self.iter_index():
            for uv in uvs:
                yield [uv.x, uv.y]

    def get_index_count(self):
        count = 0
        for indices in self.indices:
            count += len(indices)
        return count

    def iter_index(self):
        offset = 0
        for i, indices in enumerate(self.indices):
            for j in indices:
                yield j + offset
            offset += len(self.pos[i])

    def iter_face(self):
        if type(self.pos) is list:
            count = self.get_vertex_count()
            pos = (Float3 * count)()
            nom = (Float3 * count)()
            uv = (Float2 * count)()
            index = 0
            for i in range(self.pos):
                for p, n, u in zip(self.pos, self.nom, self.uv):
                    pos[index] = p
                    nom[index] = n
                    uv[index] = u
                    index += 1
            self.pos = pos
            self.nom = nom
            self.uv = uv

        for i0, i1, i2 in self.iter_triangles():
            return ([i0, i1, i2], # pos
                    [] # nom
                    [i0, i1, i2], # uv
                    None, # material
                    None, # smooth group
                    None, # obj
                    [], # ?
                    )


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
            wrap = node_shader_utils.PrincipledBSDFWrapper(
                blender_material, is_readonly=False)
            wrap.use_nodes = True
            pbr = material.pbrMetallicRoughness
            if pbr:
                if pbr.baseColorTexture.index != -1:
                    wrap.diffuse_texture.image = textures[pbr.baseColorTexture.index]
                    wrap.diffuse_texture.texcoords = 'UV'
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

            blender_mesh.vertices.add(vertices.get_vertex_count())
            positions = [x for x in vertices.iter_positions()] 
            blender_mesh.vertices.foreach_set(
                "co", positions)

            index_count = vertices.get_index_count()
            blender_mesh.loops.add(index_count)
            '''
            for f in faces:
                    vidx = f[0]
                    nbr_vidx = len(vidx)
                    loops_vert_idx.extend(vidx)
                    faces_loop_start.append(lidx)
                    faces_loop_total.append(nbr_vidx)
                    lidx += nbr_vidx
            '''
            indices = [x for x in vertices.iter_index()]
            blender_mesh.loops.foreach_set("vertex_index", indices)

            triangle_count = int(index_count / 3)
            blender_mesh.polygons.add(triangle_count)
            starts = [i * 3 for i in range(triangle_count)]
            blender_mesh.polygons.foreach_set("loop_start", starts)
            total = [3 for _ in range(triangle_count)]
            blender_mesh.polygons.foreach_set("loop_total", total)

            blen_uvs = blender_mesh.uv_layers.new()
            #blen_uvs.data.foreach_set("uv", [x for x in vertices.iter_uv()])
            for i, uv in enumerate(vertices.iter_uv()):
                blen_uvs.data[i].uv = uv
            print(blen_uvs)

            blender_mesh.validate(clean_customdata=False)  # *Very* important to not remove lnors here!
            blender_mesh.update()
            '''
            blender_mesh.polygons.foreach_set(
                "vertices", triangles)
            blender_mesh.vertices.from_pydata(
                vertices.iter_positions(),
                [],
                vertices.iter_triangles())
            '''

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
