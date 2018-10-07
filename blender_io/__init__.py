import pathlib
from typing import List, Any
from bpy_extras.image_utils import load_image
from progress_report import ProgressReport
from .. import gltftypes


def load_textures(progress: ProgressReport, base_dir: pathlib.Path, gltf: gltftypes.glTF)->List[Any]:
    progress.enter_substeps(len(gltf.textures), "Loading textures...")

    def create_texture(texture: gltftypes.Texture):
        image = gltf.images[texture.source]
        texture = load_image(image.uri, str(base_dir))
        progress.step()
        return texture
    textures = [create_texture(texture) for texture in gltf.textures]
    progress.leave_substeps()
    return textures
