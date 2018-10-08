import json
import pathlib
from typing import Set
from progress_report import ProgressReport  # , ProgressReportSubstep
from . import gltftypes, blender_io


from logging import getLogger  # pylint: disable=C0411
logger = getLogger(__name__)


def load(context, filepath: str,
         global_matrix  # pylint: disable=W0613
         )->Set[str]:
    path = pathlib.Path(filepath)
    base_dir = path.parent
    if not path.exists():
        return {'CANCELLED'}

    with ProgressReport(context.window_manager) as progress:
        progress.enter_substeps(5, "Importing GLTF %r..." % path.name)

        with path.open() as f:
            gltf = gltftypes.from_json(json.load(f))

        textures = blender_io.load_textures(progress, base_dir, gltf)

        materials = blender_io.load_materials(progress, textures, gltf)

        meshes = blender_io.load_meshes(progress, base_dir, materials, gltf)

        _objects = blender_io.load_objects(context, progress, base_dir, meshes, gltf)

        context.scene.update()

        progress.leave_substeps("Finished")
        return {'FINISHED'}
