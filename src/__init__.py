bl_info = {
    'name': 'GoldSrc Model',
    'description': 'Import Model (mdl) files used in Valve\'s GoldSrc Engine',
    'author': 'Colin Basnett',
    'version': (1, 0, 0),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export',
    'warning': 'This add-on is under development.',
    'wiki_url': 'https://github.com/cmbasnett/io_scene_mdl/wiki',
    'tracker_url': 'https://github.com/cmbasnett/io_scene_mdl/issues',
    'support': 'COMMUNITY',
    'category': 'Import-Export'
}

if 'bpy' in locals():
    import importlib
    if 'mdl'        in locals(): importlib.reload(mdl)
    if 'reader'     in locals(): importlib.reload(reader)
    if 'importer'   in locals(): importlib.reload(importer)

import os
import bpy
from . import reader
from . import importer

classes = (
    importer.MDL_OT_ImportOperator,
)


def menu_func_import(self, context):
    self.layout.operator(importer.MDL_OT_ImportOperator.bl_idname, text='GoldSrc Model (.mdl)')


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)
