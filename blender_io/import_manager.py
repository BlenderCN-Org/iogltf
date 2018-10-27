import pathlib
from typing import List, Tuple

import bpy
import mathutils  # pylint: disable=E0401

from ..gltftypes import glTF
from ..gltf_buffer import VertexBuffer


class ImportManager:
    def __init__(self, path: pathlib.Path, gltf: glTF, yup_to_zup: bool)->None:
        self.base_dir = path.parent
        self.gltf = gltf
        self.textures: List[bpy.types.Texture] = []
        self.materials: List[bpy.types.Material] = []
        self.meshes: List[Tuple[bpy.types.Mesh, VertexBuffer]] = []

        self.mod_v = lambda v: (
            v[0], v[1], v[2]) if yup_to_zup else lambda v: v
        self.mod_q = lambda q: mathutils.Quaternion(
            self.mod_v(q.axis), q.angle) if yup_to_zup else lambda q: q
