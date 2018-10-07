import os
import json
import pathlib
import importlib
import bpy
import iogltf

from logging import getLogger # pylint: disable=c0411
logger = getLogger(__name__)


importlib.reload(iogltf)


def run():
    from logging import basicConfig, DEBUG
    basicConfig(
        level=DEBUG,
        datefmt='%H:%M:%S',
        format='%(asctime)s[%(levelname)s][%(name)s.%(funcName)s] %(message)s'
    )

    logger.debug(f"#### run {__name__} ####")

    here = pathlib.Path(__file__).absolute().parent
    if here.suffix == '.blend':
        here = here.parent

    sample_folder = 'glTF-Sample-Models/2.0'
    #path = here / sample_folder / 'Avocado/glTF/Avocado.gltf'
    #path = here / sample_folder / 'DamagedHelmet/glTF/DamagedHelmet.gltf'
    #path = here / sample_folder / 'BoxAnimated/glTF/BoxAnimated.gltf'
    #path = here / sample_folder / 'Buggy/glTF/Buggy.gltf'
    #path = here / sample_folder / 'CesiumMilkTruck/glTF/CesiumMilkTruck.gltf'
    path = here / sample_folder / 'CesiumMan/glTF/CesiumMan.gltf'

    if False:
        def mesh_str(mesh):
            return ''.join(str(prim.attributes) for prim in mesh.primitives)

        for root, dirs, files in os.walk(here / sample_folder):
            root = pathlib.Path(root)
            for f in files:
                f = root / f
                if f.suffix == '.gltf':
                    import gltftypes
                    with f.open() as r:
                        gltf = gltftypes.from_json(json.load(r))
                        print(f, [mesh_str(mesh) for mesh in gltf.meshes])
    elif False:
        for root, dirs, files in os.walk(here / sample_folder):
            root = pathlib.Path(root)
            for f in files:
                f = root / f
                if f.suffix == '.gltf':
                    import gltftypes
                    with f.open() as r:
                        gltf = gltftypes.from_json(json.load(r))
                        print(f, len(gltf.skins))

    else:

        try:
            iogltf.unregister()
        except:
            pass
        iogltf.register()

        bpy.ops.import_scene.iogltf('EXEC_DEFAULT', filepath=str(path))


run()
