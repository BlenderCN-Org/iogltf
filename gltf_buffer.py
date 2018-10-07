import pathlib
import ctypes
from typing import Dict
from . import gltftypes


_buffer_map: Dict[str, bytes] = {}


def get_view_bytes(base: pathlib.Path, gltf: gltftypes.glTF, view_index: int)->bytes:
    view = gltf.bufferViews[view_index]
    buffer = gltf.buffers[view.buffer]
    if buffer.uri:
        if buffer.uri in _buffer_map:
            return _buffer_map[buffer.uri][view.byteOffset:view.byteOffset+view.byteLength]
        else:
            path = base / buffer.uri
            with path.open('rb') as f:
                data = f.read()
                _buffer_map[buffer.uri] = data
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


class VertexBuffer:
    def __init__(self, path: pathlib.Path, gltf: gltftypes.glTF, mesh: gltftypes.Mesh)->None:
        # check shared attributes
        attributes: Dict[str, int] = {}
        shared = True
        for prim in mesh.primitives:
            # print(prim.attributes)
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
            pos = get_array(
                path, gltf, prim.attributes['POSITION'], Float3)
            if 'NORMAL' in prim.attributes:
                nom = get_array(
                    path, gltf, prim.attributes['NORMAL'], Float3)
                if len(nom) != len(pos):
                    raise Exception("len(nom) different from len(pos)")
            if 'TEXCOORD_0' in prim.attributes:
                uv = get_array(
                    path, gltf, prim.attributes['TEXCOORD_0'], Float2)
                if len(uv) != len(pos):
                    raise Exception("len(uv) different from len(pos)")
            for i, _ in enumerate(pos):
                self.pos[pos_index] = pos[i].x
                pos_index += 1
                self.pos[pos_index] = -pos[i].z
                pos_index += 1
                self.pos[pos_index] = pos[i].y
                pos_index += 1

                if nom:
                    self.nom[nom_index] = nom[i].x
                    nom_index += 1
                    self.nom[nom_index] = -nom[i].z
                    nom_index += 1
                    self.nom[nom_index] = nom[i].y
                    nom_index += 1

                if uv:
                    xy = uv[i]
                    xy.y = 1.0 - xy.y
                    self.uv[uv_index] = xy
                    uv_index += 1

            #
            # indices
            #
            indices = get_indices(path, gltf, prim.indices)
            for i in indices:
                self.indices[indices_index] = offset + i
                indices_index += 1
            offset += len(pos)
