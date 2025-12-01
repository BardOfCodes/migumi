

from sysl.shader.global_shader_context import GlobalShaderContext
import migumi.symbolic as ms
import sysl.symbolic as sls
from geolipi.symbolic.base import GLFunction
import geolipi.symbolic as gls
from sysl.shader.param_evaluate import _inline_parse_param_from_expr
from geolipi.symbolic.symbol_types import (
    MOD_TYPE,
    TRANSFORM_TYPE,
)
import sys
if sys.version_info >= (3, 11):
    from functools import singledispatch
else:
    from geolipi.torch_compute.patched_functools import singledispatch
from ordered_set import OrderedSet as OSet
TRANSITION_EXPR_PROPS = {
    "in_args": "",
    "out_type": "mat4",
}



def generate_transition_code(geometry_name, inst_transition_map, global_sc : GlobalShaderContext = None, beta_mode=False):
    
    state_cases = []
    time_steps = []
    deps = []
    last_output = global_sc.local_sc.res_sdf_stack[-1]
    last_output_type, last_output_name = last_output
    for ind, (state_i, state_expr) in enumerate(inst_transition_map.items()):
        # Tiny functions.
        func_name = f"{geometry_name}_state{ind}"
        global_sc.push_codebook(func_name, TRANSITION_EXPR_PROPS)
        init_code_line = "mat4 pos_0 = mat4(1.0);"
        global_sc.local_sc.add_codeline(init_code_line)
        global_sc = rec_convert_transition(state_expr, global_sc=global_sc)
        global_sc.resolve_codebook()
        global_sc.pop_codebook()
        state_cases.append(f"case {ind}: return {geometry_name}_state{ind}();")
        time_steps.append(state_i)
        deps.append(func_name)
        global_sc.add_shader_module(func_name)
    # Now the wrappers
    deps.append(f"{geometry_name}SDF")
    # one for mapping the input to mat4s
    func_name = f"{geometry_name}Stateful"
    if len(time_steps) == 1:
        class_transition = "TransitionWrapperSingle"
        global_sc.add_shader_module(
            class_transition,
            function_name=func_name,
            geometry_name=geometry_name,
            deps=deps,
            out_type=last_output_type,
        )
    else:
        class_transition = "TransitionWrapper"
        global_sc.add_shader_module(
            class_transition,
            function_name=func_name,
            geometry_name=geometry_name,
            state_cases= "\n\t\t".join(state_cases),
            N= len(time_steps),
            time_steps= ", ".join([str(float(x)) for x in time_steps]),
            deps=deps,
            out_type=last_output_type,
        )
    global_sc.local_sc.add_dependency(class_transition)
    # second write the wrappers
    return global_sc

@singledispatch
def rec_convert_transition(expression:gls.GLFunction, global_sc:GlobalShaderContext=None) -> GlobalShaderContext:
    raise NotImplementedError

@rec_convert_transition.register
def eval_transform(expression: TRANSFORM_TYPE, global_sc:GlobalShaderContext=None):
    params = expression.args[1:]
    params = _inline_parse_param_from_expr(expression, params, global_sc)
    translation_param = params[0]
    cur_pos = global_sc.local_sc.pos_stack.pop()
    global_sc.local_sc.pos_count += 1
    new_pos_count = global_sc.local_sc.pos_count
    new_pos = f"pos_{new_pos_count}"
    if isinstance(expression, gls.Translate3D):
        func_name = "TranslationMatrix"
    elif isinstance(expression, gls.EulerRotate3D):
        func_name = "EulerRotationMatrix"
    
    code_line = f"mat4 {new_pos} = {func_name}({translation_param}) * {cur_pos};"
    global_sc.local_sc.pos_stack.append(new_pos)
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc = rec_convert_transition(expression.args[0], global_sc=global_sc)
    return global_sc

@rec_convert_transition.register
def eval_named_geometry(expression: ms.NamedGeometry, global_sc:GlobalShaderContext=None):
    cur_pos = global_sc.local_sc.pos_stack.pop()
    new_pos = "res"
    code_line = f"mat4 {new_pos} = {cur_pos};"
    global_sc.local_sc.res_sdf_stack.append(("mat4", new_pos))
    global_sc.local_sc.add_codeline(code_line)
    return global_sc