from typing import List
import pathlib

import bpy
from bpy_extras.image_utils import load_image
from progress_report import ProgressReport

from . import gltftypes
from .import_manager import ImportManager

from logging import getLogger  # pylint: disable=C0411
logger = getLogger(__name__)


def _create_texture(progress: ProgressReport,
                    manager: ImportManager,
                    index: int,
                    texture: gltftypes.Texture
                    )->bpy.types.Texture:
    image = manager.gltf.images[texture.source]
    if image.uri:
        texture = load_image(image.uri, str(manager.base_dir))
    elif image.bufferView != -1:
        if not bpy.data.filepath:
            # can not extract image files
            #raise Exception('no bpy.data.filepath')
            texture = bpy.data.images.new('image', 128, 128)

        else:

            image_dir = pathlib.Path(
                bpy.data.filepath).absolute().parent / manager.path.stem
            if not image_dir.exists():
                image_dir.mkdir()

            data = manager.get_view_bytes(image.bufferView)
            image_path = image_dir / f'texture_{index:0>2}.png'
            if not image_path.exists():
                with image_path.open('wb') as w:
                    w.write(data)

            texture = load_image(image_path.name, str(image_path.parent))
    else:
        raise Exception("invalid image")
    progress.step()
    return texture


def load_textures(progress: ProgressReport,
                  manager: ImportManager)->List[bpy.types.Texture]:

    progress.enter_substeps(len(manager.gltf.textures), "Loading textures...")
    textures = [_create_texture(progress, manager, i, texture)
                for i, texture in enumerate(manager.gltf.textures)]
    progress.leave_substeps()
    return textures
