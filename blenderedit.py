import pathlib
import importlib
import bpy
import iogltf

print('reload', iogltf)
importlib.reload(iogltf)


def run():
    print(f"#### run {__name__} ####")

    here = pathlib.Path(__file__).absolute().parent
    if here.suffix == '.blend':
        here = here.parent
    path = here / 'glTF-Sample-Models/2.0/Avocado/glTF/Avocado.gltf'

    try:
        iogltf.unregister()
    except:
        pass
    iogltf.register()

    bpy.ops.import_scene.iogltf('EXEC_DEFAULT', filepath=str(path))

run()
