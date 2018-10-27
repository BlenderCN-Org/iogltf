import pathlib
from typing import List, Tuple
import bpy
from ..gltftypes import glTF
from ..gltf_buffer import VertexBuffer


class ImportManager:
    def __init__(self, path: pathlib.Path, gltf: glTF, yup_to_zup: bool)->None:
        self.base_dir = path.parent
        self.gltf = gltf
        self.textures: List[bpy.types.Texture] = []
        self.materials: List[bpy.types.Material] = []
        self.meshes: List[Tuple[bpy.types.Mesh, VertexBuffer]] = []

    # setup from root to descendants
    def mod_v(self, v):
        # return (v[0], v[1], v[2])
        return v

    def mod_q(self, q):
        # return mathutils.Quaternion(mod_v(q.axis), q.angle)
        return q
