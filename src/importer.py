import bpy
import bpy_extras
import bmesh
import os
import math
from mathutils import Vector, Matrix, Quaternion
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, CollectionProperty
import numpy
from .reader import MdlReader
from .mdl import *


class MDL_OT_ImportOperator(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = 'io_scene_goldsrc_mdl.mdl_import'
    bl_label = 'Import GoldSrc MDL'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    # ImportHelper mixin class uses this
    filename_ext = '.mdl'

    filter_glob: StringProperty(
        default="*.mdl",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be hilighted.
    )
    should_import_textures: BoolProperty(default=True)
    should_import_geometry: BoolProperty(default=True)
    should_import_hitboxes: BoolProperty(default=True)
    should_import_skeleton: BoolProperty(default=True)
    should_import_attachments: BoolProperty(default=True)
    should_import_materials: BoolProperty(default=True)

    def import_mdl(self, mdl):
        model_name = os.path.splitext(os.path.basename(mdl.file_path))[0]
        armature = bpy.data.armatures.new(model_name)
        armature_object = bpy.data.objects.new(model_name, armature)
        armature_object.show_in_front = True
        collection = bpy.context.scene.collection
        collection.objects.link(armature_object)
        armature_object.select_set(True)
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.object.mode_set(mode='EDIT')

        materials = []
        for texture in mdl.textures:
            material = bpy.data.materials.new(texture.filename.decode())
            material.specular_intensity = 0.0
            material.use_nodes = True

            ''' Create texture '''
            image = bpy.data.images.new(texture.filename.decode(), texture.width, texture.height)
            image.pixels = texture.data

            materials.append(material)

            node_tree = material.node_tree

            output = node_tree.nodes['Material Output']

            # Remove the Principled BSDF node
            principled_bsdf = node_tree.nodes['Principled BSDF']
            node_tree.nodes.remove(principled_bsdf)

            diffuse_bsdf = node_tree.nodes.new('ShaderNodeBsdfDiffuse')

            texture_image = node_tree.nodes.new('ShaderNodeTexImage')
            texture_image.image = image

            node_tree.links.new(diffuse_bsdf.inputs['Color'], texture_image.outputs['Color'])
            node_tree.links.new(output.inputs['Surface'], diffuse_bsdf.outputs['BSDF'])

        for bone in mdl.bones:
            edit_bone = armature.edit_bones.new(bone.name.decode())

            if bone.parent_index >= 0:
                edit_bone.parent = armature.edit_bones[bone.parent_index]  # TODO: how does this not crash?

            edit_bone.tail = (0, 2, 0)
            edit_bone.transform(Matrix(bone.transform))

        if self.should_import_hitboxes:
            for mdl_hitbox in mdl.hitboxes:
                center = bounding_box_center(mdl_hitbox.bounding_box)
                extents = bounding_box_extents(mdl_hitbox.bounding_box)
                hitbox_bone = mdl.bones[mdl_hitbox.bone_index]
                hitbox_object = bpy.data.objects.new(f'HB_{hitbox_bone.name.decode()}', None)
                hitbox_object.empty_display_type = 'CUBE'
                hitbox_object.show_in_front = True

                child_of_constraint = hitbox_object.constraints.new('CHILD_OF')
                child_of_constraint.target = armature_object
                child_of_constraint.subtarget = hitbox_bone.name.decode()

                hitbox_object.location = center
                hitbox_object.scale = extents

                collection.objects.link(hitbox_object)
                hitbox_object.parent = armature_object

        bpy.ops.object.mode_set(mode='OBJECT')

        if self.should_import_attachments:
            for attachment in mdl.attachments:
                attachment_object = bpy.data.objects.new(attachment.name.decode(), None)
                attachment_object.parent = armature_object  # TODO: not strictly necessary
                attachment_object.location = attachment.location
                child_of_constraint = attachment_object.constraints.new('CHILD_OF')
                child_of_constraint.target = armature_object
                child_of_constraint.subtarget = mdl.bones[attachment.bone_index].name.decode()
                collection.objects.link(attachment_object)

        if self.should_import_geometry:
            for body_part in mdl.body_parts:
                # TODO: collection for body parts?? maybe an empty?? one big mesh?
                for model in body_part.models:
                    for mesh in model.meshes:
                        model_name = f'{body_part.name.decode()}_{model.name.decode()}'
                        mesh_data = bpy.data.meshes.new(model_name)
                        mesh_object = bpy.data.objects.new(model_name, mesh_data)

                        mesh_data.uv_layers.new()

                        # Create vertex groups for each bone
                        for bone in mdl.bones:
                            mesh_object.vertex_groups.new(name=bone.name.decode())

                        bm = bmesh.new()
                        bm.from_mesh(mesh_data)

                        # Add material
                        mesh_data.materials.append(materials[mesh.texture_index])

                        for vertex_index, vertex in enumerate(model.vertices):
                            vertex_bone = mdl.bones[model.vertex_bone_indices[vertex_index]]
                            v = vertex_bone.transform.dot(numpy.array(vertex + (1,)))
                            bm.verts.new(v[:3])

                        bm.verts.ensure_lookup_table()

                        texture = mdl.textures[mesh.texture_index]
                        uvs = []

                        triangle_hashes = set()

                        for face in mesh.faces:
                            triangles = []
                            is_face_clockwise = True
                            face_uvs = []
                            if face.primitive_type == PrimitiveType.TRIANGLE_STRIP:
                                for i in range(len(face.vertices) - 2):
                                    face_vertices = face.vertices[i:i + 3]
                                    if is_face_clockwise:
                                        face_vertices[1:] = face_vertices[1:][::-1]
                                    triangles.append([v.vertex_index for v in face_vertices])
                                    face_uvs.extend([(fv.u / texture.width, 1.0 - fv.v / texture.height) for fv in face_vertices])
                                    is_face_clockwise = not is_face_clockwise
                            elif face.primitive_type == PrimitiveType.TRIANGLE_FAN:
                                face_vertices = [face.vertices[0], None, None]
                                for i in range(1, len(face.vertices) - 1):
                                    face_vertices[1] = face.vertices[i]
                                    face_vertices[2] = face.vertices[i + 1]
                                    triangles.append([v.vertex_index for v in face_vertices][::-1])
                                    face_uvs.extend([(fv.u / texture.width, 1.0 - fv.v / texture.height) for fv in face_vertices][::-1])

                            # TODO: move the actual creation of the faces to *after* the fact
                            for triangle_index in range(len(triangles)):
                                triangle = triangles[triangle_index]
                                indices = list(sorted(triangle))
                                # Calculate the unique hash for the triangle
                                triangle_hash = (indices[0]) | (indices[1] << 12) | (indices[2] << 24)
                                if triangle_hash in triangle_hashes:
                                    d = len(bm.verts)
                                    a = bm.verts[triangle[0]].co
                                    b = bm.verts[triangle[1]].co
                                    c = bm.verts[triangle[2]].co
                                    bm.verts.new(a)
                                    bm.verts.new(b)
                                    bm.verts.new(c)
                                    triangles[triangle_index] = [d + 0, d + 1, d + 2]
                                    bm.verts.ensure_lookup_table()
                                else:
                                    triangle_hashes.add(triangle_hash)

                            uvs.extend(face_uvs)

                            for triangle in triangles:
                                bm.faces.new((bm.verts[triangle[0]], bm.verts[triangle[1]], bm.verts[triangle[2]]))

                        bm.faces.ensure_lookup_table()

                        mesh_data.validate(clean_customdata=False)
                        mesh_data.update(calc_edges=False)

                        bm.to_mesh(mesh_data)
                        collection.objects.link(mesh_object)

                        '''
                        Assign texture coordinates.
                        '''
                        uv_texture = mesh_data.uv_layers[0]
                        for i, uv in enumerate(uvs):
                            uv_texture.data[i].uv = uv

                        ''' Add an armature modifier. '''
                        armature_modifier = mesh_object.modifiers.new(name='Armature', type='ARMATURE')
                        armature_modifier.object = armature_object

                        ''' Assign vertex weighting. '''
                        for (vertex_index, vertex_bone_index) in enumerate(model.vertex_bone_indices):
                            vertex_group_name = mdl.bones[vertex_bone_index].name.decode()  # TODO: slow
                            vertex_group = mesh_object.vertex_groups[vertex_group_name]
                            vertex_group.add([vertex_index], 1.0, 'REPLACE')

                        mesh_object.parent = armature_object

                    break

        bpy.ops.object.mode_set(mode='OBJECT')


    def execute(self, context):
        mdl = MdlReader.from_file(self.filepath)
        self.import_mdl(mdl)
        return {'FINISHED'}