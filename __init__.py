import bpy
from bpy.props import (
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
if "import_gltf" in locals():
    print('reload', 'import_gltf')
    import importlib
    importlib.reload(import_gltf)
    importlib.reload(gltftypes)


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


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportGLTF(bpy.types.Operator, ImportHelper):
    """Load a GLTF"""
    bl_idname = "import_scene.iogltf"
    bl_label = "Import GLTF"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gltf"
    filter_glob: StringProperty(default="*.gltf", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(
            ignore=(
                "axis_forward",
                "axis_up",
                "filter_glob",
            )
        )
        global_matrix = axis_conversion(
            from_forward=self.axis_forward,
            from_up=self.axis_up,
        ).to_4x4()

        keywords["global_matrix"] = global_matrix

        from . import gltftypes
        from . import import_gltf
        return import_gltf.load(context, **keywords)


def menu_func_import(self, context):
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
