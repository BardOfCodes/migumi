import os
import torch as th
import matplotlib.colors

import geolipi.symbolic.combinators as sym_comb
import geolipi.symbolic.primitives_3d as sym_prim3d
import geolipi.symbolic.primitives_2d as sym_prim2d
import geolipi.symbolic.transforms_3d as sym_t3d
import geolipi.symbolic.transforms_2d as sym_t2d
import geolipi.symbolic.primitives_higher as sym_higher
import geolipi.symbolic.color as sym_color
import migumi.symbolic as ms
import string
from . import function_wrappers as fw

# Try compile
# PRIMITIVE_MAP = {x: th.compile(y) for x, y in PRIMITIVE_MAP.items()}

def translate_func_3d(shader_code_store, translation_param):
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    code_line = f"vec3 {new_pos} = {cur_pos} - {translation_param};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    return shader_code_store

def translate_func_2d(shader_code_store, translation_param):
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    code_line = f"vec2 {new_pos} = {cur_pos} - {translation_param};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    return shader_code_store

def euler_rotate_func_3d(shader_code_store, rotate_param):
    """
    Adds GLSL code for EulerRotate3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the rotation angles (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    
    # GLSL code for Euler rotation (param[0] is the vec3 rotation angles)
    code_line = f"vec3 {new_pos} = Rotate3D({cur_pos}, {rotate_param});"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Rotate3D")
    return shader_code_store

def euler_rotate_func_2d(shader_code_store, rotate_param):
    """
    Adds GLSL code for EulerRotate2D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the rotation angles (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    
    # GLSL code for Euler rotation (param[0] is the vec3 rotation angles)
    code_line = f"vec2 {new_pos} = Rotate2D({cur_pos}, {rotate_param});"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Rotate2D")
    return shader_code_store

def scale_func_3d(shader_code_store, param):
    """
    Adds GLSL code for Scale3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the scale factors (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    
    # GLSL code for scaling (param[0] is the vec3 scale factors)
    code_line = f"vec3 {new_pos} = {cur_pos} / {param};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    return shader_code_store

def scale_func_2d(shader_code_store, param):
    """
    Adds GLSL code for Scale2D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the scale factors (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    
    # GLSL code for scaling (param[0] is the vec3 scale factors)
    code_line = f"vec2 {new_pos} = {cur_pos} / {param};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    return shader_code_store

def dilate_func_2d(shader_code_store, k):
    """
    Adds GLSL code for Scale2D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the scale factors (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    sdf_name_1 = shader_code_store.sdf_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    code_line = f"float {sdf_name} = {sdf_name_1} - {k};"
    shader_code_store.codebook.append(code_line)
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store


MODIFIER_MAP = {
    sym_t3d.Translate3D: translate_func_3d,
    sym_t3d.EulerRotate3D: euler_rotate_func_3d,
    sym_t3d.Scale3D: scale_func_3d,
    sym_t2d.Translate2D: translate_func_2d,
    sym_t2d.EulerRotate2D: euler_rotate_func_2d,
    sym_t2d.Scale2D: scale_func_2d,
    sym_t2d.Dilate2D: dilate_func_2d,

}

def sdf3d_sphere(shader_code_store, sphere_param):
    """
    Adds GLSL code for Sphere3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        sphere_param: A list containing the sphere parameters (vec4).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1

    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = Sphere3D({cur_pos}, {sphere_param});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Sphere3D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf2d_circle(shader_code_store, sphere_param):
    """
    Adds GLSL code for Sphere3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        sphere_param: A list containing the sphere parameters (vec4).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1

    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = Circle2D({cur_pos}, {sphere_param});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Circle2D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store


def sdf3d_box(shader_code_store, box_param):
    """
    Adds GLSL code for Sphere3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        sphere_param: A list containing the sphere parameters (vec4).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1

    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = Box3D({cur_pos}, {box_param});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Box3D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf3d_obox(shader_code_store, box_scale, box_origin):
    """
    Adds GLSL code for Sphere3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        sphere_param: A list containing the sphere parameters (vec4).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1

    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = OBox3D({cur_pos}, {box_scale}, {box_origin});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("OBox3D")
    shader_code_store.sdf_stack.append(sdf_name)    
    return shader_code_store


def sdf3d_superprimitve(shader_code_store, size_param, corner_param, thickness_param, mode_param, extrusion_param, onion_param, inflate_param):
    
    cur_pos = shader_code_store.pos_stack.pop()
    
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    mode_param = int(float(mode_param))
        
    code_line = f"float {sdf_name} = SuperPrimitive3D({cur_pos}, {size_param}, {corner_param}, {thickness_param}, {mode_param}, {extrusion_param}, {onion_param}, {inflate_param});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("SuperPrimitive3D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf3d_linked_height_field(shader_code_store, plane_origin, plane_normal):
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    shader_code_store.pos_stack.append(new_pos)

    code_line = f"vec3 {new_pos} = LocalHFCoord({cur_pos}, {plane_origin}, {plane_normal});"
    shader_code_store.codebook.append(code_line)
    code_line = f"vec2 {new_pos}_xy = {new_pos}.xy;"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("LocalHFCoord")
    newer_pos = f"{new_pos}_xy"
    shader_code_store.pos_stack.append(newer_pos)
    return shader_code_store

def sdf3d_bboxed_linked_height_field(shader_code_store, plane_origin, plane_normal, bbox_scale, bbox_origin):
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    shader_code_store.pos_stack.append(new_pos)
    
    
    code_line = f"vec3 {new_pos} = BBoxedLocalHFCoord({cur_pos}, {plane_origin}, {plane_normal}, {bbox_scale}, {bbox_origin});"
    shader_code_store.codebook.append(code_line)
    code_line = f"vec2 {new_pos}_xy = {new_pos}.xy;"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("BBoxedLocalHFCoord")
    newer_pos = f"{new_pos}_xy"
    shader_code_store.pos_stack.append(newer_pos)
    return shader_code_store

def sdf3d_apply_height(shader_code_store, height):
    sdf2d = shader_code_store.sdf_stack.pop()
    pos3d = shader_code_store.pos_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    code_line = f"float {sdf_name} = ApplyHeight({pos3d}, {sdf2d}, {height});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("ApplyHeight")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf2d_box2d(shader_code_store, rect_param):
    
    cur_pos = shader_code_store.pos_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = Rectangle2D({cur_pos}, {rect_param});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Rectangle2D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store


def sdf2d_trapezoid(shader_code_store, r1, r2, height):
    
    cur_pos = shader_code_store.pos_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = Trapezoid2D({cur_pos}, {r1}, {r2}, {height});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Trapezoid2D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def SetMaterial(shader_code_store, material_id):

    cur_sdf = shader_code_store.sdf_stack.pop()
    
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"vec2 res = SetMaterial({cur_sdf}, {material_id});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("SetMaterial")
    return shader_code_store

def MaskableSetMaterial(shader_code_store, material_id):
    
    cur_sdf = shader_code_store.sdf_stack.pop()
    
    ind = shader_code_store.n_masked_geoms
    func_name = f"masker_{ind}"
    bool_name = f"_MASK_{ind}"
    shader_code_store.n_masked_geoms += 1
    
    code_lines = string.Template(fw.MaskableSetMaterial).substitute(
        {'name': func_name, 'bool_name': bool_name}
    )
    shader_code_store.custom_functions.append(code_lines)

    code_line = f"vec2 res = {func_name}({cur_sdf}, {material_id});"
    shader_code_store.codebook.append(code_line)
    return shader_code_store



def sdf2d_polyarc(shader_code_store, vec_list, num_points):
    
    cur_pos = shader_code_store.pos_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    
    # GLSL code for polyline Fragment
    func_name = f"polyarc_custom_{len(shader_code_store.custom_functions)}"
    code_lines = string.Template(fw.PolyArc2DInner).substitute(
        {'name': func_name, 'n_points': num_points}
    )
    # split into lines
    shader_code_store.custom_functions.append(code_lines)

    code_line = f"float {sdf_name} = {func_name}({cur_pos}, {vec_list});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("PolyArc2D")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

PRIMITIVE_MAP = {
    sym_prim3d.Sphere3D: sdf3d_sphere,
    sym_prim2d.Circle2D: sdf2d_circle,
    sym_prim3d.Box3D: sdf3d_box,
    sym_prim2d.Rectangle2D: sdf2d_box2d,
    sym_prim2d.Trapezoid2D: sdf2d_trapezoid,
    ms.LinkedHeightField3D: sdf3d_linked_height_field,
    ms.ApplyHeight: sdf3d_apply_height,
    ms.SetMaterial: SetMaterial,
    sym_prim2d.PolyArc2D: sdf2d_polyarc,

}

def sdf_union(shader_code_store, n_children, *args, **kwargs):
    # Need to know how many to use. 
    children = [shader_code_store.sdf_stack.pop() for _ in range(n_children)]
    # sdf_name_2, sdf_name_1 = shader_code_store.sdf_stack.pop(), shader_code_store.sdf_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    sdf_names = ", ".join(children)
    code_line = f"float {sdf_name} = Union({sdf_names});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Union")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf_intersection(shader_code_store, n_children, *args, **kwargs):
    children = [shader_code_store.sdf_stack.pop() for _ in range(n_children)]
    # sdf_name_2, sdf_name_1 = shader_code_store.sdf_stack.pop(), shader_code_store.sdf_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    sdf_names = ", ".join(children)
    code_line = f"float {sdf_name} = Intersection({sdf_names});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Intersection")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf_difference(shader_code_store, n_children, *args, **kwargs):
    sdf_name_2, sdf_name_1 = shader_code_store.sdf_stack.pop(), shader_code_store.sdf_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    code_line = f"float {sdf_name} = Difference({sdf_name_1}, {sdf_name_2});"
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("Difference")
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

def sdf_complement(shader_code_store, *args, **kwargs):
    sdf_name_1 = shader_code_store.sdf_stack.pop()
    sdf_name = f"sdf_{shader_code_store.sdf_count}"
    shader_code_store.sdf_count += 1
    code_line = f"float {sdf_name} = -{sdf_name_1};"
    shader_code_store.codebook.append(code_line)
    shader_code_store.sdf_stack.append(sdf_name)
    return shader_code_store

COMBINATOR_MAP = {
    sym_comb.Union: sdf_union,
    sym_comb.Intersection: sdf_intersection,
    sym_comb.Difference: sdf_difference,
    sym_comb.Complement: sdf_complement,
}


def transition_translate_func_3d(shader_code_store, translation_param):
    # No need of position stack
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    code_line = f"mat4 {new_pos} = TranslationMatrix({translation_param}) * {cur_pos};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("TranslationMatrix")
    return shader_code_store


def transition_euler_rotate_func_3d(shader_code_store, rotate_param):
    """
    Adds GLSL code for EulerRotate3D operation.

    Parameters:
        shader_code_store: A utility class to track positions, code lines, and the stack.
        param: A list containing the rotation angles (vec3).

    Returns:
        Updated shader_code_store with new position and code line.
    """
    cur_pos = shader_code_store.pos_stack.pop()
    shader_code_store.pos_count += 1
    new_pos_count = shader_code_store.pos_count
    new_pos = f"pos_{new_pos_count}"
    
    # GLSL code for Euler rotation (param[0] is the vec3 rotation angles)
    code_line = f"mat4 {new_pos} = EulerRotationMatrix({rotate_param}) * {cur_pos};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)
    shader_code_store.tracked_functions.add("EulerRotationMatrix")
    return shader_code_store

def transition_named_geometry(shader_code_store, name):
    cur_pos = shader_code_store.pos_stack.pop()
    # GLSL code for Euler rotation (param[0] is the vec3 rotation angles)
    new_pos = "res"
    code_line = f"mat4 {new_pos} = {cur_pos};"
    shader_code_store.pos_stack.append(new_pos)
    shader_code_store.codebook.append(code_line)

    return shader_code_store

TRANSITION_MAP = {
    sym_t3d.Translate3D: transition_translate_func_3d,
    sym_t3d.EulerRotate3D: transition_euler_rotate_func_3d,
    ms.NamedGeometry: transition_named_geometry
    
}