# https://github.com/ZeqMacaw/Crowbar/blob/master/Crowbar/Core/GameModel/SourceModel10/SourceMdlFile10.vb

from ctypes import *
from enum import Enum
import numpy
import math


def bounding_box_center(bb):
    return (bb.min[0] + bb.max[0]) / 2, \
           (bb.min[1] + bb.max[1]) / 2, \
           (bb.min[2] + bb.max[2]) / 2


def bounding_box_extents(bb):
    return (bb.max[0] - bb.min[0]) / 2, \
           (bb.max[1] - bb.min[1]) / 2, \
           (bb.max[2] - bb.min[2]) / 2


class BoundingBox(Structure):
    _fields_ = [
        ('min', c_float * 3),
        ('max', c_float * 3)
    ]


class Hitbox(Structure):
    _fields_ = [
        ('bone_index', c_int32),
        ('group_index', c_int32),
        ('bounding_box', BoundingBox)
    ]


class Texture(Structure):
    _fields_ = [
        ('filename', c_char * 64),
        ('flags', c_int32),
        ('width', c_int32),
        ('height', c_int32),
        ('data_offset', c_int32)
    ]


class Header(Structure):
    _fields_ = [
        ('magic', c_char * 4),
        ('version', c_int32),
        ('name', c_char * 64),
        ('file_size', c_int32),
        ('eye_location', c_float * 3),
        ('hull', BoundingBox),
        ('view', BoundingBox),
        ('flags', c_int32),
        ('bone_count', c_int32),
        ('bone_offset', c_int32),
        ('bone_controller_count', c_int32),
        ('bone_controller_offset', c_int32),
        ('hitbox_count', c_int32),
        ('hitbox_offset', c_int32),
        ('sequence_count', c_int32),
        ('sequence_offset', c_int32),
        ('sequence_group_count', c_int32),
        ('sequence_group_offset', c_int32),
        ('texture_count', c_int32),
        ('texture_offset', c_int32),
        ('texture_data_offset', c_int32),
        ('skin_reference_count', c_int32),
        ('skin_family_count', c_int32),
        ('skin_offset', c_int32),
        ('body_part_count', c_int32),
        ('body_part_offset', c_int32),
        ('attachment_count', c_int32),
        ('attachment_offset', c_int32),
        ('sound_table', c_int32),
        ('sound_offset', c_int32),
        ('sound_groups', c_int32),
        ('sound_group_offset', c_int32),
        ('transition_count', c_int32),
        ('transition_offset', c_int32),
    ]


class Bone(Structure):
    _fields_ = [
        ('name', c_char * 32),
        ('parent_index', c_int32),
        ('flags', c_int32),
        ('bone_controllers', c_int32 * 6),
        ('location', c_float * 3),
        ('rotation', c_float * 3),
        ('location_scale', c_float * 3),
        ('rotation_scale', c_float * 3)
    ]


class BoneController(Structure):
    _fields_ = [
        ('bone_index', c_int32),
        ('type', c_int32),
        ('start_angle', c_float),
        ('end_angle', c_float),
        ('rest_index', c_int32),
        ('index', c_int32)
    ]


class Sequence(Structure):
    _fields_ = [
        ('name', c_char * 32),
        ('fps', c_float),
        ('flags', c_int32),
        ('activity_id', c_int32),
        ('activity_weight', c_int32),
        ('event_count', c_int32),
        ('event_offset', c_int32),
        ('frame_count', c_int32),
        ('pivot_count', c_int32),
        ('pivot_offset', c_int32),
        ('motion_type', c_int32),
        ('motion_bone', c_int32),
        ('linear_movement', c_float * 3),
        ('auto_move_pos_index', c_int32),
        ('auto_move_angle_index', c_int32),
        ('bounding_box', BoundingBox),
        ('blend_count', c_int32),
        ('anim_offset', c_int32),
        ('blend_type', c_int32 * 2),
        ('blend_start', c_float * 2),
        ('blend_end', c_float * 2),
        ('blend_parent', c_int32),
        ('group_index', c_int32),
        ('entry_node_index', c_int32),
        ('exit_node_index', c_int32),
        ('node_flags', c_int32),
        ('next_sequence', c_int32)
    ]


class SequenceEvent(Structure):
    _fields_ = [
        ('frame_index', c_int32),
        ('event_index', c_int32),
        ('event_type', c_int32),
        ('options', c_char * 64)
    ]


class SequencePivot(Structure):
    _fields_ = [
        ('location', c_float * 3),
        ('start', c_int32),
        ('end', c_int32)
    ]


class BodyPart(Structure):
    _fields_ = [
        ('name', c_char * 64),
        ('model_count', c_int32),
        ('base', c_int32),
        ('model_offset', c_int32)
    ]


class Attachment(Structure):
    _fields_ = [
        ('name', c_char * 32),
        ('type', c_int32),
        ('bone_index', c_int32),
        ('location', c_float * 3),
        ('vectors', (c_float * 3) * 3)  # TODO: maybe a 3x3 rotation matrix?
    ]


class Model(Structure):
    _fields_ = [
        ('name', c_char * 64),
        ('type', c_int32),
        ('bounding_radius', c_float),
        ('mesh_count', c_int32),
        ('mesh_offset', c_int32),
        ('vertex_count', c_int32),
        ('vertex_bone_indices_offset', c_int32),
        ('vertex_offset', c_int32),
        ('normal_count', c_int32),
        ('normal_bone_info_offset', c_int32),
        ('normal_offset', c_int32),
        ('group_count', c_int32),
        ('group_offset', c_int32)
    ]


class Mesh(Structure):
    _fields_ = [
        ('face_count', c_int32),
        ('face_offset', c_int32),
        ('texture_index', c_int32),
        ('normal_count', c_int32),
        ('normal_offset', c_int32)
    ]


class PrimitiveType(Enum):
    TRIANGLE_FAN = 0
    TRIANGLE_STRIP = 1


class Face(object):
    def __init__(self):
        self.primitive_type = PrimitiveType.TRIANGLE_STRIP
        self.vertices = []


class FaceVertex(Structure):
    _fields_ = [
        ('vertex_index', c_uint16),
        ('normal_index', c_uint16),
        ('u', c_uint16),
        ('v', c_uint16)
    ]


class Animation(object):
    def __init__(self):
        self.values = [[]] * 6


class AnimationValueData(Structure):
    _fields_ = [
        ('value', c_uint16)
    ]


class AnimationValueHeader(Structure):
    _fields_ = [
        ('valid', c_uint8),
        ('total', c_uint8)
    ]


class AnimationValue(Union):
    _fields_ = [
        ('data', AnimationValueData),
        ('header', AnimationValueHeader)
    ]


class BonePose(object):
    def __init__(self):
        self.location = numpy.array(3)
        self.rotation = numpy.array(3)
        self.rotation_quat = numpy.array(4)


# TODO: move this shit elsewhere
def calc_matrix(px, py, pz, rx, ry, rz):
    cos = math.cos
    sin = math.sin
    return numpy.array([
        [cos(ry) * cos(rz), sin(rx) * sin(ry) * cos(rz) + cos(rx) * -sin(rz), cos(rx) * sin(ry) * cos(rz) + -sin(rx) * -sin(rz), px],
        [cos(ry) * sin(rz), sin(rx) * sin(ry) * sin(rz) + cos(rx) * cos(rz), cos(rx) * sin(ry) * sin(rz) + -sin(rx) * cos(rz), py],
        [-sin(ry), sin(rx) * cos(ry), cos(rx) * cos(ry), pz],
        [0, 0, 0, 1]
    ])


def get_bone_transform(bone):
    rx, ry, rz = bone.rotation  # roll, pitch, yaw
    px, py, pz = bone.location
    return calc_matrix(px, py, pz, rx, ry, rz)


class Mdl(object):
    def __init__(self):
        self.file_path = ''
        self.bones = []
        self.bone_controllers = []
        self.hitboxes = []
        self.sequences = []
        self.textures = []
        self.skin_families = []
        self.body_parts = []

    def calc_bone_matrices(self, sequence_index: int, blend_index: int, frame_index: int):
        sequence = self.sequences[sequence_index]
        for bone_index, bone in enumerate(self.bones):
            animation = sequence.animations[blend_index * len(self.bones) + bone_index]
            location, rotation = calc_bone_matrix(frame_index, bone, animation)
            # TODO: create a matrix right here


# TODO: this can probably be simplified to be all encompassing
def calc_bone_matrix(frame_index: int, bone, animation):
    px, py, pz = bone.location
    rx, ry, rz = bone.rotation
    if animation.value_offsets[0] > 0:
        px = extract_animation_value(frame_index, animation.values[0], bone.location_scale[0], bone.location[0])
    if animation.value_offsets[1] > 0:
        py = extract_animation_value(frame_index, animation.values[1], bone.location_scale[1], bone.location[1])
    if animation.value_offsets[2] > 0:
        pz = extract_animation_value(frame_index, animation.values[2], bone.location_scale[2], bone.location[2])
    if animation.value_offsets[3] > 0:
        rx = extract_animation_value(frame_index, animation.values[3], bone.rotation_scale[0], bone.rotation[0])
    if animation.value_offsets[4] > 0:
        ry = extract_animation_value(frame_index, animation.values[4], bone.rotation_scale[1], bone.rotation[1])
    if animation.value_offsets[5] > 0:
        rz = extract_animation_value(frame_index, animation.values[5], bone.rotation_scale[2], bone.rotation[2])
    return calc_matrix(px, py, pz, rx, ry, rz)


def extract_animation_value(frame_index: int, values, scale: float, base_value: float):
    k = frame_index
    value_index = 0
    while values[value_index].header.total <= k:
        k -= values[value_index].header.total
        value_index += values[value_index].header.value + 1
        if value_index >= len(values) or values[value_index].header.total == 0:
            raise RuntimeError('uh oh')
    if values[value_index].header.valid > k:
        return values[value_index + k + 1].data.value * scale + base_value
    else:
        return values[value_index + values[value_index].header.valid].header.value * scale + base_value
