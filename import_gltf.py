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

        objects = blender_io.load_objects(progress, meshes, gltf)

        # link objects to scene
        view_layer = context.view_layer
        if view_layer.collections.active:
            collection = view_layer.collections.active.collection
        else:
            collection = context.scene.master_collection.new()
            view_layer.collections.link(collection)
        for obj in objects:
            collection.objects.link(obj)
            obj.select_set('SELECT')
            # we could apply this anywhere before scaling.
            #obj.matrix_world = global_matrix

        context.scene.update()

        progress.leave_substeps("Finished")
        return {'FINISHED'}
