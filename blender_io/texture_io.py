from typing import List

import bpy
from bpy_extras.image_utils import load_image
from progress_report import ProgressReport

from .. import gltftypes
from .import_manager import ImportManager

from logging import getLogger  # pylint: disable=C0411
logger = getLogger(__name__)


def _create_texture(progress: ProgressReport,
                    manager: ImportManager,
                    texture: gltftypes.Texture)->bpy.types.Texture:
    image = manager.gltf.images[texture.source]
    texture = load_image(image.uri, str(manager.base_dir))
    progress.step()
    return texture


def load_textures(progress: ProgressReport,
                  manager: ImportManager)->List[bpy.types.Texture]:

    progress.enter_substeps(len(manager.gltf.textures), "Loading textures...")
    textures = [_create_texture(progress, manager, texture)
                for texture in manager.gltf.textures]
    progress.leave_substeps()
    return textures
