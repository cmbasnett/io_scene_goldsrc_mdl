from .mdl import *
from ctypes import sizeof
from typing import Type
from mathutils import Euler, Matrix
import struct
import math
import numpy


def unpack(fmt, f):
    return struct.unpack(fmt, f.read(struct.calcsize(fmt)))


def read_chunk(file, offset: int, cls: Type[Structure], count: int):
    file.seek(offset)
    return [cls.from_buffer_copy(file.read(sizeof(cls))) for _ in range(count)]


def get_bone_transform(bone):
    r, p, y = bone.rotation
    px, py, pz = bone.location
    rotation_matrix = Euler((r, p, y), 'XYZ').to_matrix().to_4x4()
    translation_matrix = Matrix.Translation((px, py, pz))
    return rotation_matrix @ translation_matrix


class MdlReader(object):

    @staticmethod
    def from_file(path: str):
        mdl = Mdl()
        mdl.file_path = path
        expected_version = 10
        with open(path, 'rb') as f:
            header = Header.from_buffer_copy(f.read(sizeof(Header)))
            if header.version != expected_version:
                raise RuntimeError(f'MDL version not supported (found: {header.version}, expected {expected_version})')
            mdl.bones = read_chunk(f, header.bone_offset, Bone, header.bone_count)
            mdl.bone_controllers = read_chunk(f, header.bone_controller_offset, BoneController, header.bone_controller_count)
            mdl.hitboxes = read_chunk(f, header.hitbox_offset, Hitbox, header.hitbox_count)
            mdl.sequences = read_chunk(f, header.sequence_offset, Sequence, header.sequence_count)

            for sequence in mdl.sequences:
                sequence.events = read_chunk(f, sequence.event_offset, SequenceEvent, sequence.event_count)
                sequence.pivots = read_chunk(f, sequence.pivot_offset, SequencePivot, sequence.pivot_count)

            mdl.textures = read_chunk(f, header.texture_offset, Texture, header.texture_count)
            mdl.skin_families = [unpack(f'{header.skin_reference_count}H', f) for _ in range(header.skin_family_count)]
            mdl.body_parts = read_chunk(f, header.body_part_offset, BodyPart, header.body_part_count)
            mdl.attachments = read_chunk(f, header.attachment_offset, Attachment, header.attachment_count)

            for texture in mdl.textures:
                f.seek(texture.data_offset)
                pixels = list(f.read(texture.width * texture.height))
                palette = numpy.ndarray((256, 3), dtype=numpy.uint8, buffer=f.read(256 * 3))
                data = numpy.ones((texture.height, texture.width, 4))
                j = 0
                for y in range(texture.height):
                    for x in range(texture.width):
                        data[y][x][:3] = [x / 255 for x in palette[pixels[j]]]
                        j += 1
                texture.data = numpy.flip(data, axis=0).flatten()

            for body_part in mdl.body_parts:
                body_part.models = read_chunk(f, body_part.model_offset, Model, body_part.model_count)
                for model in body_part.models:
                    model.meshes = read_chunk(f, model.mesh_offset, Mesh, model.mesh_count)
                    # vertices
                    f.seek(model.vertex_offset)
                    model.vertices = list(struct.iter_unpack('3f', f.read(struct.calcsize('3f') * model.vertex_count)))
                    # vertex bone indices
                    f.seek(model.vertex_bone_indices_offset)
                    model.vertex_bone_indices = list(f.read(model.vertex_count))
                    # normals
                    f.seek(model.normal_offset)
                    model.normals = list(struct.iter_unpack('3f', f.read(struct.calcsize('3f') * model.normal_count)))
                    for mesh in model.meshes:
                        # faces
                        f.seek(mesh.face_offset)
                        mesh.faces = []
                        while True:
                            face_vertex_count = unpack('h', f)[0]
                            if face_vertex_count == 0:
                                break
                            face = Face()
                            if face_vertex_count < 0:
                                face.primitive_type = PrimitiveType.TRIANGLE_FAN
                            else:
                                face.primitive_type = PrimitiveType.TRIANGLE_STRIP
                            face_vertex_count = abs(face_vertex_count)
                            face.vertices = read_chunk(f, f.tell(), FaceVertex, face_vertex_count)
                            mesh.faces.append(face)

            # Read sequences
            sequence_group_index = 0
            for sequence in mdl.sequences:
                if sequence.group_index != sequence_group_index:
                    continue
                f.seek(sequence.anim_offset)
                sequence.animations = []
                for blend_index in range(sequence.blend_count):
                    for _ in range(header.bone_count):
                        animation_file_offset = f.tell()
                        animation = Animation()
                        # There are 6 channels, px, py, pz, rx, ry, rz (r values are euler angles)
                        for offset_index in range(len(animation.value_offsets)):
                            animation.value_offsets[offset_index] = unpack('h', f)[0]
                            if animation.value_offsets[offset_index] > 0:
                                pos = f.tell()
                                f.seek(animation_file_offset + animation.value_offsets[offset_index])
                                animation.values[offset_index] = read_animation_values(sequence.frame_count, f)
                                f.seek(pos)
                        sequence.animations.append(animation)

        # Calculate bone transforms
        for bone in mdl.bones:
            bone.local_transform = get_bone_transform(bone)
            if bone.parent_index >= 0:
                parent_bone_transform = mdl.bones[bone.parent_index].transform
            else:
                parent_bone_transform = Matrix.Identity(4)
            # TODO: backwards??
            bone.transform = parent_bone_transform @ bone.local_transform

        return mdl


def read_animation_values(frame_count, f):
    animation_values = []
    while frame_count > 0:
        value = AnimationValue.from_buffer_copy(f.read(sizeof(AnimationValue)))
        if value.header.total == 0:
            raise RuntimeError('an error occurred while reading animation values')
        frame_count -= value.header.total
        animation_values.append(value)
        if value.header.valid > 0:
            # TODO: this needs to be the structs
            animation_values.extend(read_chunk(f, f.tell(), AnimationValue, value.header.valid))
    return animation_values
