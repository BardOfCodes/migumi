## What must the shader contain? 
## All the other code components
## Main Fragment
import string
import sympy as sp
import torch as th
from geolipi.symbolic.base import GLFunction
import geolipi.symbolic as gls
from ordered_set import OrderedSet as OSet

from geolipi.symbolic.symbol_types import (
    MACRO_TYPE,
    MOD_TYPE,
    PRIM_TYPE,
    COMBINATOR_TYPE,
    TRANSFORM_TYPE,
    POSITIONALMOD_TYPE,
    SDFMOD_TYPE,
)
from geolipi.torch_compute.maps import MODIFIER_MAP, PRIMITIVE_MAP, COMBINATOR_MAP

import migumi.symbolic as ms
from .utils import MODIFIER_MAP, PRIMITIVE_MAP, COMBINATOR_MAP, TRANSITION_MAP
from . import function_wrappers as fw # function_map, main_wrapper_template

MOTION_FUNCTIONS = OSet(["Slerp", "QuatRotationMatrix", "RotationFromMatrix", "InterpAffine", "ApplyAffine"])
BOX_THRESH = 0.1

class ShaderCodeStore:

    def __init__(self):
        self.codebook = []
        self.tracked_functions = OSet(['iBox', "Box3D", "MinRes", "BoundingBox3D"])
        self.custom_functions = []
        self.tracked_variables = []
        self.pos_stack = ["pos_0"]
        self.sdf_stack = []
        self.final_output = None
        
        self.sdf_count = 0
        self.pos_count = 0
        self.uniforms = {}
        self.n_masked_geoms = 0
    
    def convert_uniforms(self):
        uniform_lines = []
        for key, value in self.uniforms.items():
            uniform_line = f"uniform {value['type']} {key};"
            uniform_lines.append(uniform_line)
        return "\n".join(uniform_lines)
    
    def add_bbox(self, bbox, geometry_name):
        if len(bbox) == 2:
            # it has scale and origin
            bbox_scale = bbox[0]
            bbox_origin = bbox[1]
            bbox_scale = _inline_parse_param_from_expr(None, tuple([bbox_scale,]), self)
            bbox_origin = _inline_parse_param_from_expr(None, tuple([bbox_origin,]), self)
            code_lines = "\n".join(self.codebook)
            bbox_func = string.Template(fw.BOUNDING_BOX_BETA_WRAPPER).substitute({
                "geometry_name": geometry_name,
                "bbox_scale": bbox_scale[0],
                "bbox_origin": bbox_origin[0]
            })
            self.custom_functions.append(bbox_func)
        else:
            
            bbox_param = _inline_parse_param_from_expr(None, tuple([bbox,]), self)
            code_lines = "\n".join(self.codebook)
            bbox_func = string.Template(fw.BOUNDING_BOX_WRAPPER).substitute({
                "geometry_name": geometry_name,
                "code_lines": code_lines,
                "bbox_param": bbox_param[0]
            })
            self.custom_functions.append(bbox_func)

    def refresh(self):
        """
        Update all expect Tracked Functions and custom functions
        """
        self.codebook = []
        # self.tracked_functions = OSet(['iBox', "Box3D", "MinRes"])
        # self.custom_functions = []
        # self.tracked_variables = []
        self.pos_stack = ["pos_0"]
        self.sdf_stack = []
        self.final_output = None
        self.sdf_count = 0
        self.pos_count = 0
        # self.uniforms = {}

    def convert_to_sdf_function(self, function_name):
        code_list = self.codebook
        code_lines = "\n".join(code_list)
        sdf_func_code = string.Template(fw.SDF_FUNCTION_WRAPPER)
        sdf_func_code = sdf_func_code.substitute({
            'code_lines': code_lines,
            'function_name': function_name
        })
        return sdf_func_code
    def convert_to_transition_function(self, function_name):
        code_list = self.codebook
        code_lines = "\n".join(code_list)
        sdf_func_code = string.Template(fw.TRANSITION_FUNCTION_WRAPPER)
        sdf_func_code = sdf_func_code.substitute({
            'code_lines': code_lines,
            'function_name': function_name
        })
        return sdf_func_code

    
def generate_transition_code(geometry_name, inst_transition_map, shader_code_store : ShaderCodeStore = None, beta_mode=False):

    if shader_code_store is None:
        shader_code_store = ShaderCodeStore()
    # Add the motion specific functions
    
    shader_code_store.tracked_functions.update(MOTION_FUNCTIONS)
    # First convert each state expr to a shader function
    state_cases = []
    time_steps = []
    for ind, (state_i, state_expr) in enumerate(inst_transition_map.items()):
        shader_code_store = recursive_convert_transition(state_expr, shader_code_store=shader_code_store)
        sdf_func_code = shader_code_store.convert_to_transition_function(f"{geometry_name}_state{ind}")
        shader_code_store.custom_functions.append(sdf_func_code)
        shader_code_store.refresh()
        state_cases.append(f"case {ind}: return {geometry_name}_state{ind}();")
        time_steps.append(state_i)

    # Now the wrappers
    # one for mapping the input to mat4s
    if len(time_steps) == 1:
        if beta_mode:
            wrapper = fw.TRANSITION_STATE_BETA_WRAPPER_SINGLE
        else:
            wrapper = fw.TRANSITION_STATE_WRAPPER_SINGLE
        transition_state_func = string.Template(wrapper).substitute({
            "geometry_name": geometry_name,
        })
    else:
        if beta_mode:
            wrapper = fw.TRANSITION_STATE_BETA_WRAPPER
        else:
            wrapper = fw.TRANSITION_STATE_WRAPPER
        transition_state_func = string.Template(wrapper).substitute({
            "geometry_name": geometry_name,
            "state_cases": "\n\t\t".join(state_cases),
            "N": len(time_steps),
            "time_steps": ", ".join([str(float(x)) for x in time_steps])
        })
    shader_code_store.custom_functions.append(transition_state_func)
    # second write the wrappers
    return shader_code_store
    

def recursive_convert_transition(expression, shader_code_store=None):

    if shader_code_store is None:
        shader_code_store = ShaderCodeStore()
    
    if isinstance(expression, MOD_TYPE):
        sub_expr = expression.args[0]
        params = expression.args[1:]
        params = _inline_parse_param_from_expr(expression, params, shader_code_store)
        # This is a hack unclear how to deal with other types)
        if isinstance(expression, TRANSFORM_TYPE):
            shader_code_store = TRANSITION_MAP[type(expression)](shader_code_store, *params)
            return recursive_convert_transition(sub_expr, shader_code_store,)
    elif isinstance(expression, ms.NamedGeometry):
        # create sdf and return.

        params = [expression.args[0].name,]
        shader_code_store = TRANSITION_MAP[type(expression)](shader_code_store, *params)
        return shader_code_store
    else:
        raise NotImplementedError

def recursive_convert_to_shader(
    expression: GLFunction,
    shader_code_store = None,

):
    """
    Recursively evaluates a GeoLIPI expression to generate a signed distance field (SDF) or a color canvas.

    This function can handles all GeoLIPI operations but is slower than the other evaluation methods.

    Parameters:
        expression (GLFunction): The GLFunction expression to evaluate.
        sketcher (Sketcher): Primary sketcher object for SDF or color generation.
        secondary_sketcher (Sketcher, optional): Secondary sketcher for higher-order primitives.
        initialize (bool): Flag to initialize coordinates and scale if True. Used for the first call.
        rectify_transform (bool): Flag to rectify transformations.
        coords (th.Tensor, optional): Coordinates for evaluation. If None, generated from sketcher.
        tracked_scale (th.Tensor, optional): Scale tracking tensor. If None, generated from sketcher.
        relaxed_occupancy (bool): Flag to use relaxed occupancy for soft SDFs. Useful with Parameter Optimization of SVG expressions.
        relax_temperature (float): Temperature parameter for relaxed occupancy. Defaults to 0.0.

    Returns:
        th.Tensor: The resulting SDF or color canvas from evaluating the expression.
    """
    if shader_code_store is None:
        shader_code_store = ShaderCodeStore()
    

    if isinstance(expression, MACRO_TYPE):
        raise NotImplementedError
    elif isinstance(expression, MOD_TYPE):
        sub_expr = expression.args[0]
        params = expression.args[1:]
        params = _inline_parse_param_from_expr(expression, params, shader_code_store)
        # This is a hack unclear how to deal with other types)
        if isinstance(expression, TRANSFORM_TYPE):
            shader_code_store = MODIFIER_MAP[type(expression)](shader_code_store, *params)
            return recursive_convert_to_shader(
                sub_expr,
                shader_code_store=shader_code_store,
            )
        elif isinstance(expression, POSITIONALMOD_TYPE):
            raise NotImplementedError
        elif isinstance(expression, SDFMOD_TYPE):
            sub_expr = expression.args[0]
            params = expression.args[1:]
            params = _inline_parse_param_from_expr(expression, params, shader_code_store)
            # This is a hack unclear how to deal with other types)
            shader_code_store = recursive_convert_to_shader(
                sub_expr,
                shader_code_store=shader_code_store,
            )
            shader_code_store = MODIFIER_MAP[type(expression)](shader_code_store, *params)
            return shader_code_store
    elif isinstance(expression, PRIM_TYPE):
        # create sdf and return.

        params = expression.args
        if isinstance(expression, gls.PolyArc2D):
            params = (gls.VecList(params[0], len(params[0])),)
        params = _inline_parse_param_from_expr(expression, params, shader_code_store)

        shader_code_store = PRIMITIVE_MAP[type(expression)](shader_code_store, *params)
        return shader_code_store
    elif isinstance(expression, COMBINATOR_TYPE):
        # what about parameterized combinators?
        tree_branches, param_list = [], []
        for arg in expression.args:
            if arg in expression.lookup_table:
                param_list.append(expression.lookup_table[arg])
            else:
                tree_branches.append(arg)
        # the pos has to be copied
        cur_pos = shader_code_store.pos_stack.pop()
        
        for child in tree_branches:
            shader_code_store.pos_stack.append(cur_pos)

            shader_code_store = recursive_convert_to_shader(
                child,
                shader_code_store=shader_code_store,
            )

        shader_code_store = COMBINATOR_MAP[type(expression)](shader_code_store, len(tree_branches), *param_list)
        return shader_code_store
    elif isinstance(expression, ms.LinkedHeightField3D):
        plane = expression.args[0]
        apply_height_expr = expression.args[1]
        plane_args = _inline_parse_param_from_expr(plane, plane.args, shader_code_store)

        shader_code_store = PRIMITIVE_MAP[type(expression)](shader_code_store, *plane_args)
        # This now has the local coordinates. 
        height = _inline_parse_param_from_expr(plane, apply_height_expr.args[1:], shader_code_store)[0]

        inner_expr = apply_height_expr.args[0]

        # Eval of the inner expression
        shader_code_store = recursive_convert_to_shader(
                inner_expr,
                shader_code_store=shader_code_store,
            )
        shader_code_store = PRIMITIVE_MAP[type(apply_height_expr)](shader_code_store, height)
        return shader_code_store
    
    elif isinstance(expression, ms.SetMaterial):

        inner_expr = expression.args[0]
        shader_code_store = recursive_convert_to_shader(
                inner_expr,
                shader_code_store=shader_code_store,
            )
        params = expression.args[1:]
        params = _inline_parse_param_from_expr(expression, params, shader_code_store)
        shader_code_store = PRIMITIVE_MAP[type(expression)](shader_code_store, *params)
        return shader_code_store

    elif isinstance(expression, gls.UniformFloat):

        inner_expr = expression.args[0]
        shader_code_store = recursive_convert_to_shader(
                inner_expr,
                shader_code_store=shader_code_store,
            )
        params = expression.args[1:]
        params, shader_code_store = _inline_parse_param_from_expr(expression, params, shader_code_store)
        shader_code_store = PRIMITIVE_MAP[type(expression)](shader_code_store, *params)
        return shader_code_store
    elif isinstance(expression, ms.MarkerNode):

        sub_expr = expression.args[0]
        shader_code_store = recursive_convert_to_shader(
            sub_expr,
            shader_code_store=shader_code_store,
        )
        return shader_code_store
    else:
        raise NotImplementedError

    

uniform_type_map = {
    gls.UniformFloat: "float",
    gls.UniformVec2: "vec2",
    gls.UniformVec3: "vec3",
    gls.UniformVec4: "vec4",
}

# A mapper from operation type to shader line template
map_op_map = {
    "ADD": "{expr1} + {expr2}",
    "SUB": "{expr1} - {expr2}",
    "MUL": "{expr1} * {expr2}",
    "DIV": "{expr1} / {expr2}",
    "POW": "pow({expr1}, {expr2})",
    "NEG": "-{expr}",
    "SIN": "sin({expr})",
    "COS": "cos({expr})",
    "TAN": "tan({expr})",
    "ASIN": "asin({expr})",
    "ACOS": "acos({expr})",
    "ATAN": "atan({expr})",
    "ATAN2": "atan({expr1}, {expr2})",
    "LOG": "log({expr})",
    "EXP": "exp({expr})",
    "SQRT": "sqrt({expr})",
    "ABS": "abs({expr})",
    "MIN": "min({expr1}, {expr2})",
    "MAX": "max({expr1}, {expr2})",
    "FLOOR": "floor({expr})",
    "CEIL": "ceil({expr})",
    "ROUND": "round({expr})",
    "FRAC": "fract({expr})",
    "SIGN": "sign({expr})",
    "STEP": "step({expr1}, {expr2})",
    "MOD": "mod({expr1}, {expr2})",
    "NORMALIZE": "normalize({expr})",
    "NORM": "length({expr})",
}

def recursive_parse_param(expression, params, shader_code_store):
    shader_params = []
    for ind, param in enumerate(params):
        if isinstance(param, (tuple, sp.Tuple)):
            processed_param = param_primitive_process(param)
            shader_params.append(processed_param)
        elif isinstance(param, str):
            # Are we sure?
            shader_params.append(param)
        elif isinstance(param, sp.Symbol):
            if param in expression.lookup_table:
                cur_param = expression.lookup_table[param]
                processed_param = param_primitive_process(cur_param)
                shader_params.append(processed_param)
            else:
                shader_params.append(param.name)
        elif isinstance(param, (sp.Integer, sp.Float)):
            if isinstance(param, sp.Integer):
                param = float(param)
            processed_param = f"{param}"
            shader_params.append(processed_param)
        elif isinstance(param, (gls.VecList)):
            vector_list, n_vecs = param.args
            under_params = vector_list
            under_expression = param
            cur_params, shader_code_store = recursive_parse_param(under_expression, under_params, shader_code_store)
            varname = f"var_{len(shader_code_store.tracked_variables)}"
            shader_code_store.tracked_variables.append(varname)
            vec_type = f"vec{len(vector_list[0])}"
            vec_line = f"const {vec_type}[] {varname} = {vec_type}[]({', '.join(cur_params)});"
            shader_code_store.codebook.append(vec_line)
            shader_params.append(varname)
            shader_params.append(str(n_vecs))
        elif isinstance(param, (gls.UniformFloat, gls.UniformVec2, gls.UniformVec3, gls.UniformVec4)):
            min_val, default_val, max_val, uniform_name = param.args
            uniform_name = uniform_name.name
            arg_type = uniform_type_map[type(param)]
            uniform_entry = {'type': arg_type, "init_value": [float(x) for x in default_val], 
                                "min": [float(x) for x in min_val], "max": [float(x) for x in max_val]}
            if isinstance(param, gls.UniformFloat):
                uniform_entry["init_value"] = uniform_entry["init_value"][0]
            shader_code_store.uniforms.update({uniform_name: uniform_entry})
            shader_params.append(uniform_name)
        elif isinstance(param, (gls.Float, gls.Vec2, gls.Vec3, gls.Vec4)):
            # Now its input can be a math node, or a variable. 
            under_expression = param
            under_params = param.args
            cur_params, shader_code_store = recursive_parse_param(under_expression, under_params, shader_code_store)
            if isinstance(param, gls.Float):
                shader_params.append(cur_params[0])
            elif isinstance(param, gls.Vec2):
                new_param = f"vec2({cur_params[0]}, {cur_params[1]})"
                shader_params.append(new_param)
            elif isinstance(param, gls.Vec3):
                new_param = f"vec3({cur_params[0]}, {cur_params[1]}, {cur_params[2]})"
                shader_params.append(new_param)
            elif isinstance(param, gls.Vec4):
                new_param = f"vec4({cur_params[0]}, {cur_params[1]}, {cur_params[2]}, {cur_params[3]})"
                shader_params.append(new_param)
            else:
                raise NotImplementedError
        elif isinstance(param, gls.VarSplitter):
            under_expression = param
            under_params = param.args
            cur_params, shader_code_store = recursive_parse_param(under_expression, under_params, shader_code_store)
            selected_ind = int(float(cur_params[1]))
            new_param = cur_params[0]
            if selected_ind == 0:
                shader_params.append(f"{new_param}.x")
            elif selected_ind == 1:
                shader_params.append(f"{new_param}.y")
            elif selected_ind == 2:
                shader_params.append(f"{new_param}.z")
            elif selected_ind == 3:
                shader_params.append(f"{new_param}.w")
            else:
                raise NotImplementedError
        elif isinstance(param, (gls.UnaryOperator, gls.VectorOperator)):
            under_expression = param
            under_params = param.args
            cur_params, shader_code_store = recursive_parse_param(under_expression, under_params, shader_code_store)
            new_param = cur_params[0]
            op = cur_params[1]
            op_template = map_op_map[op]
            shader_line = op_template.format(expr=new_param)
            shader_params.append(shader_line)
        elif isinstance(param, gls.BinaryOperator):
            under_expression = param
            under_params = param.args
            cur_params, shader_code_store = recursive_parse_param(under_expression, under_params, shader_code_store)
            new_param1 = cur_params[0]
            new_param2 = cur_params[1]
            op = cur_params[2]
            op_template = map_op_map[op]
            shader_line = op_template.format(expr1=new_param1, expr2=new_param2)
            shader_params.append(shader_line)
        else:
            print(f"DEBUG: recursive_parse_param: {param}")
            raise NotImplementedError
            
    return shader_params, shader_code_store


def _inline_parse_param_from_expr(expression, params, shader_code_store=None):
    shader_params, shader_code_store = recursive_parse_param(expression, params, shader_code_store)
    return shader_params

def param_primitive_process(param):

    if isinstance(param, str):
        shader_line = f"{param}"
    else:
        if len(param) == 0:
            if isinstance(param, sp.Integer):
                param = float(param)
            shader_line = f"{param}"
        if len(param) == 1:
            if isinstance(param[0], sp.Integer):
                param = [float(param[0])]
            shader_line = f"{param[0]}"
        elif len(param) == 2:
            shader_line = f"vec2({param[0]}, {param[1]})"
        elif len(param) == 3:
            shader_line = f"vec3({param[0]}, {param[1]}, {param[2]})"
        elif len(param) == 4:
            shader_line = f"vec4({param[0]}, {param[1]}, {param[2]}, {param[3]})"
        else:
            print(f"DEBUG: param_primitive_process: {param}")
            raise NotImplementedError
    return shader_line
