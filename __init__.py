import bpy
from bpy.props import (  # pylint: disable=E0401
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper,
    axis_conversion,
)
if "blender_io" in locals():
    print('reload', 'blender_io')
    import importlib
    importlib.reload(gltftypes)  # pylint: disable=E0601
    importlib.reload(blender_io)  # pylint: disable=E0601
    importlib.reload(gltf_buffer)  # pylint: disable=E0601

    importlib.reload(texture_io)  # pylint: disable=E0601
    importlib.reload(material_io)  # pylint: disable=E0601
    importlib.reload(mesh_io)  # pylint: disable=E0601
    importlib.reload(node_io)  # pylint: disable=E0601
    importlib.reload(node)  # pylint: disable=E0601
    importlib.reload(import_manager)  # pylint: disable=E0601

from . import gltftypes, blender_io, gltf_buffer  # pylint: disable=C0413
from .blender_io import texture_io, material_io, mesh_io, node_io, node, import_manager


bl_info = {
    "name": "IO GL Transmission Format (GLTF)",
    "author": "ousttrue",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import-Export GLTF from objects",
    "warning": "",
    "wiki_url": "https://github.com/ousttrue/iogltf",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


class ImportGLTF(bpy.types.Operator):
    """Load a GLTF"""
    bl_idname = "import_scene.iogltf"
    bl_label = "Import GLTF"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gltf"
    filter_glob = StringProperty(default="*.gltf", options={'HIDDEN'})
    filepath = StringProperty(
        name="File Path",
        description="Filepath used for importing the file",
        maxlen=1024,
        subtype='FILE_PATH',
    )

    yup_to_zup = BoolProperty(default=True)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        keywords = self.as_keywords(
            ignore=(
                "filter_glob",
                'axis_forward',
                'axis_up'
            )
        )
        return blender_io.load(context, **keywords)


def menu_func_import(self, _context):
    self.layout.operator(ImportGLTF.bl_idname,
                         text="GL Transmission Format (.gltf)")


# def menu_func_export(self, context):
#    self.layout.operator(ExportBVH.bl_idname, text="Motion Capture (.bvh)")


CLASSES = (
    ImportGLTF,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    # bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


def main():
    import pathlib
    import sys
    here = pathlib.Path(__file__).absolute().parent
    if here.suffix == '.blend':
        here = here.parent
    if str(here) not in sys.path:
        sys.path.append(str(here))
    register()


if __name__ == "__main__":
    main()
