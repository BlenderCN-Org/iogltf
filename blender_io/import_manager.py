import pathlib
import ctypes
from typing import List, Tuple, Dict, Any

import bpy
import mathutils  # pylint: disable=E0401

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


class Float4(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float),
    ]

    def __getitem__(self, i: int)->float:
        if i == 0:
            return self.x
        elif i == 1:
            return self.y
        elif i == 2:
            return self.z
        elif i == 3:
            return self.w
        else:
            raise IndexError()


class Mat16(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("f00", ctypes.c_float),
        ("f01", ctypes.c_float),
        ("f02", ctypes.c_float),
        ("f03", ctypes.c_float),
        ("f10", ctypes.c_float),
        ("f11", ctypes.c_float),
        ("f12", ctypes.c_float),
        ("f13", ctypes.c_float),
        ("f20", ctypes.c_float),
        ("f21", ctypes.c_float),
        ("f22", ctypes.c_float),
        ("f23", ctypes.c_float),
        ("f30", ctypes.c_float),
        ("f31", ctypes.c_float),
        ("f32", ctypes.c_float),
        ("f33", ctypes.c_float),
    ]


class UShort4(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_ushort),
        ("y", ctypes.c_ushort),
        ("z", ctypes.c_ushort),
        ("w", ctypes.c_ushort),
    ]

    def __getitem__(self, i: int)->int:
        if i == 0:
            return self.x
        elif i == 1:
            return self.y
        elif i == 2:
            return self.z
        elif i == 3:
            return self.w
        else:
            raise IndexError()


def get_accessor_type_to_count(accessor_type: gltftypes.Accessor_type)->int:
    if accessor_type == gltftypes.Accessor_type.SCALAR:
        return 1
    elif accessor_type == gltftypes.Accessor_type.VEC2:
        return 2
    elif accessor_type == gltftypes.Accessor_type.VEC3:
        return 3
    elif accessor_type == gltftypes.Accessor_type.VEC4:
        return 4
    elif accessor_type == gltftypes.Accessor_type.MAT2:
        return 4
    elif accessor_type == gltftypes.Accessor_type.MAT3:
        return 9
    elif accessor_type == gltftypes.Accessor_type.MAT4:
        return 16
    else:
        raise Exception()


def get_accessor_component_type_to_len(component_type: gltftypes.Accessor_componentType)->int:
    if component_type == gltftypes.Accessor_componentType.BYTE:
        return 1
    elif component_type == gltftypes.Accessor_componentType.SHORT:
        return 2
    elif component_type == gltftypes.Accessor_componentType.UNSIGNED_BYTE:
        return 1
    elif component_type == gltftypes.Accessor_componentType.UNSIGNED_SHORT:
        return 2
    elif component_type == gltftypes.Accessor_componentType.UNSIGNED_INT:
        return 4
    elif component_type == gltftypes.Accessor_componentType.FLOAT:
        return 4
    else:
        raise NotImplementedError()


def get_accessor_byteslen(accessor: gltftypes.Accessor)->int:
    return (accessor.count
            * get_accessor_type_to_count(accessor.type)
            * get_accessor_component_type_to_len(accessor.componentType))


class ImportManager:
    def __init__(self, path: pathlib.Path,
                 gltf: gltftypes.glTF, body: bytes,
                 yup_to_zup: bool)->None:
        self.base_dir = path.parent
        self.gltf = gltf
        self.body = body
        self.textures: List[bpy.types.Texture] = []
        self.materials: List[bpy.types.Material] = []
        self.meshes: List[Tuple[bpy.types.Mesh, Any]] = []

        self.yup_to_zup = yup_to_zup
        if self.yup_to_zup:
            self.mod_v = lambda v: (v[0], -v[2], v[1])
            self.mod_q = lambda q: mathutils.Quaternion(
                self.mod_v(q.axis), q.angle)
        else:
            self.mod_v = lambda v: v
            self.mod_q = lambda q: q

        self._buffer_map: Dict[str, bytes] = {}

    def get_view_bytes(self, view_index: int)->bytes:
        view = self.gltf.bufferViews[view_index]
        buffer = self.gltf.buffers[view.buffer]
        if buffer.uri:
            if buffer.uri in self._buffer_map:
                return self._buffer_map[buffer.uri][view.byteOffset:view.byteOffset+view.byteLength]
            else:
                path = self.base_dir / buffer.uri
                with path.open('rb') as f:
                    data = f.read()
                    self._buffer_map[buffer.uri] = data
                    return data[view.byteOffset:
                                view.byteOffset+view.byteLength]
        else:
            return self.body[view.byteOffset:
                             view.byteOffset+view.byteLength]

    def get_array(self, accessor_index: int):
        accessor = self.gltf.accessors[accessor_index]
        accessor_byte_len = get_accessor_byteslen(accessor)
        view_bytes = self.get_view_bytes(accessor.bufferView)
        segment = view_bytes[accessor.byteOffset:
                             accessor.byteOffset + accessor_byte_len]

        if accessor.type == gltftypes.Accessor_type.SCALAR:
            if (accessor.componentType == gltftypes.Accessor_componentType.SHORT
                    or accessor.componentType == gltftypes.Accessor_componentType.UNSIGNED_SHORT):
                return (ctypes.c_ushort *  # type: ignore
                        accessor.count).from_buffer_copy(segment)
            elif accessor.componentType == gltftypes.Accessor_componentType.UNSIGNED_INT:
                return (ctypes.c_uint *  # type: ignore
                        accessor.count).from_buffer_copy(segment)
        elif accessor.type == gltftypes.Accessor_type.VEC2:
            if accessor.componentType == gltftypes.Accessor_componentType.FLOAT:
                return (Float2 *  # type: ignore
                        accessor.count).from_buffer_copy(segment)

        elif accessor.type == gltftypes.Accessor_type.VEC3:
            if accessor.componentType == gltftypes.Accessor_componentType.FLOAT:
                return (Float3 *  # type: ignore
                        accessor.count).from_buffer_copy(segment)

        elif accessor.type == gltftypes.Accessor_type.VEC4:
            if accessor.componentType == gltftypes.Accessor_componentType.FLOAT:
                return (Float4 *  # type: ignore
                        accessor.count).from_buffer_copy(segment)

            elif accessor.componentType == gltftypes.Accessor_componentType.UNSIGNED_SHORT:
                return (UShort4 *  # type: ignore
                        accessor.count).from_buffer_copy(segment)

        elif accessor.type == gltftypes.Accessor_type.MAT4:
            if accessor.componentType == gltftypes.Accessor_componentType.FLOAT:
                return (Mat16 *  # type: ignore
                        accessor.count).from_buffer_copy(segment)

        raise NotImplementedError()
