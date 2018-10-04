import pathlib
import bpy

import iogltf
print('reload', iogltf)
import importlib
importlib.reload(iogltf)

print(f"#### run {__file__} ####")

here = pathlib.Path(__file__).absolute().parent.parent
path = here / 'glTF-Sample-Models/2.0/Avocado/glTF/Avocado.gltf'

try:
    iogltf.unregister()
except:
    pass
iogltf.register()

bpy.ops.import_scene.iogltf('EXEC_DEFAULT', filepath=str(path))
