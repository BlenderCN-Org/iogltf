import json
import pathlib
from typing import Set

from progress_report import ProgressReport, ProgressReportSubstep
from bpy_extras.image_utils import load_image

from . import gltftypes


def load(context, filepath: str, global_matrix)->Set[str]:
    path = pathlib.Path(filepath)
    if not path.exists():
        return {'CANCELLED'}

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(1, "Importing GLTF %r..." % filepath)

        progress.enter_substeps(3, "Parsing GLTF file...")
        with path.open() as f:
            gltf = gltftypes.from_json(json.load(f))
        base_dir = path.parent

        progress.step("Done, loading images:%i..." % len(gltf.images))

        def load_texture(texture: gltftypes.Texture):
            image = gltf.images[texture.source]
            texture = load_image(image.uri, str(base_dir))
            return texture
        textures = [load_texture(texture) for texture in gltf.textures]
        print(textures)

        progress.step("Done, building geometries (mesh:%i) ..." %
                      (len(gltf.meshes)))

        return {'FINISHED'}
