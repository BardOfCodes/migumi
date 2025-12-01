## What must the shader contain? 
## All the other code components
## Main Fragment
import geolipi.symbolic as gls
from sysl.shader.evaluate import rec_shader_eval
from sysl.shader.param_evaluate import _inline_parse_param_from_expr
from sysl.shader.global_shader_context import GlobalShaderContext
import migumi.symbolic as ms
import sysl.symbolic as sls

from .transition_evaluate import generate_transition_code
from .state_based_converter import state_converter

from sysl.shader.global_shader_context import GlobalShaderContext
from sysl.shader.evaluate import rec_shader_eval, main_image_map, SCENE_EXPR_PROPS




def compile_set(expression_dict, state_map, settings=None, 
return_shader_context=False):
    # compile the expression to shader code
    if settings is None:
        settings = {}

    per_inst_motion_map = state_converter(state_map)
    global_sc = GlobalShaderContext()
    main_lines = []
    master_sdf_counter = 0
    for ind, (geometry_name, expression) in enumerate(expression_dict.items()):
        if geometry_name in per_inst_motion_map:
            cur_expr_name = f"{geometry_name}SDF"
            global_sc.push_codebook(cur_expr_name, SCENE_EXPR_PROPS)
            global_sc = rec_shader_eval(expression, global_sc=global_sc)
            last_output = global_sc.local_sc.res_sdf_stack[-1]
            last_output_type, last_output_name = last_output
            global_sc.resolve_codebook()
            global_sc.pop_codebook()
            global_sc.local_sc.add_dependency(cur_expr_name)
            # And this is all just to get the SCENE_EXPRESSION.
            output_name = f"res_{master_sdf_counter}"
            main_line = f"{last_output_type} {output_name} = {geometry_name}Stateful(pos_0, globalStateStep);"
            global_sc.local_sc.res_sdf_stack.append((last_output_type, output_name))
            global_sc.local_sc.add_codeline(main_line)
            master_sdf_counter += 1

            inst_transition_map = per_inst_motion_map[geometry_name]
            global_sc = generate_transition_code(geometry_name, inst_transition_map, global_sc)

    n_children = master_sdf_counter
    output_type, output_name = last_output_type, last_output_name
    children = [global_sc.local_sc.res_sdf_stack.pop() for _ in range(n_children)]
    # reverse the children
    children = children[::-1]
    child_names = [child[1] for child in children]
    child_types = [child[0] for child in children]

    child_type = child_types[0]
    res_sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    res_sdf_names = ", ".join(child_names)
    func_name = "Union"
    code_line = f"{child_type} {res_sdf_name} = {func_name}({res_sdf_names});"
    global_sc.local_sc.add_codeline(code_line)
    input_format = (child_type, n_children)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name, input_format=input_format)
    global_sc.local_sc.res_sdf_stack.append((child_type, res_sdf_name))
    

    global_sc.resolve_codebook() # This will finins ahd add the function.
    

    min_global_step = min([v for v in state_map.keys()])
    max_global_step = max([v for v in state_map.keys()])
    global_sc.uniforms["globalStateStep"] = {
        "type": "float",
        "init_value": 0.0,
        'min': [min_global_step,],
        "max": [max_global_step,]
    }
    render_mode = settings.get("render_mode", "v1")
    if render_mode in ["v1", "v2"]:
        global_sc.add_shader_module(main_image_map[render_mode])
    elif render_mode in ["v3", "v4"]:
        global_sc.resolve_material_stack(version=render_mode)
        global_sc.add_shader_module(main_image_map[render_mode])
    else:
        raise ValueError(f"Invalid render mode: {render_mode}")
    
    shader_code = global_sc.emit_shader_code(settings)

    with open("shader_code.glsl", "w") as f:
        f.write(shader_code)

    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    if return_shader_context:
        return shader_code, uniforms, textures, global_sc
    else:
        return shader_code, uniforms, textures
    

@rec_shader_eval.register
def eval_polyarc(expression: gls.PolyArc2D, global_sc:GlobalShaderContext=None):
    params = expression.args
    if isinstance(expression, gls.PolyArc2D):
        params = (gls.VecList(params[0], len(params[0])),)
    params = _inline_parse_param_from_expr(expression, params, global_sc)
    func_name = expression.__class__.__name__
    cur_pos = global_sc.local_sc.pos_stack.pop()
    sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    vec_list, num_points = params

    custom_func_name = f"polyarc_custom_{global_sc.custom_func_count}"
    global_sc.custom_func_count += 1
    code_line = f"float {sdf_name} = {custom_func_name}({cur_pos},{vec_list});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.local_sc.res_sdf_stack.append(("float", sdf_name))

    global_sc.add_shader_module(func_name, 
        function_name=custom_func_name, 
        num_points=num_points
    )
    return global_sc

@rec_shader_eval.register
def eval_linked_hf(expression: ms.LinkedHeightField3D, global_sc:GlobalShaderContext=None):
    plane = expression.args[0]
    apply_height_expr = expression.args[1]
    inner_expr = apply_height_expr.args[0]

    plane_args = _inline_parse_param_from_expr(plane, plane.args, global_sc)
    primitive_param = ",".join(plane_args)
    func_name = "LocalHFCoord"
    cur_pos = global_sc.local_sc.pos_stack.pop()
    global_sc.local_sc.pos_count += 1
    new_pos = f"pos_{global_sc.local_sc.pos_count}"
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"vec3 {new_pos} = {func_name}({cur_pos}, {primitive_param});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.pos_stack.append(new_pos)
    code_line = f"vec2 {new_pos}_xy = {new_pos}.xy;"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    global_sc.local_sc.pos_stack.append(f"{new_pos}_xy")

    # Eval of the inner expression
    global_sc = rec_shader_eval(inner_expr, global_sc=global_sc)

    height = _inline_parse_param_from_expr(plane, apply_height_expr.args[1:], global_sc)[0]
    pos3d = global_sc.local_sc.pos_stack.pop()
    sdf2d = global_sc.local_sc.res_sdf_stack.pop()
    
    sdf2d_type, sdf2d_name = sdf2d
    func_name = "ApplyHeight"
    sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    
    code_line = f"{sdf2d_type} {sdf_name} = {func_name}({pos3d}, {sdf2d_name}, {height});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    global_sc.local_sc.res_sdf_stack.append((sdf2d_type, sdf_name))
    return global_sc


@rec_shader_eval.register
def eval_mxg_function(expression: ms.MarkerNode, global_sc:GlobalShaderContext=None):
    inner_expr = expression.args[0]
    global_sc = rec_shader_eval(inner_expr, global_sc=global_sc)
    return global_sc


