from sysl.shader.evaluate_multipass import posttrace_map
from sysl.shader.global_shader_context import GlobalShaderContext
from sysl.shader.evaluate_singlepass import rec_shader_eval, main_image_map, SCENE_EXPR_PROPS
from sysl.shader.evaluate_multipass import rec_sdf_shader_eval
from .state_based_converter import state_converter
from .transition_evaluate import generate_transition_code
from sysl.shader.shader_templates import imfx_shaders as imfx_shaders
from typing import Union as type_union
from typing import Tuple, Dict, Any, List
import geolipi.symbolic as gls
import migumi.symbolic as ms
from sysl.shader.param_evaluate import _inline_parse_param_from_expr
from sysl.shader.evaluate_multipass import create_third_pass_shader_bundle, create_aa_pass_shader_bundle


@rec_sdf_shader_eval.register
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

    # prim_name = f"prim_{global_sc.prim_count}"
    # code_line = f"vec2 {prim_name} = vec2({sdf_name}, {global_sc.prim_count});"
    # global_sc.local_sc.add_codeline(code_line)
    # global_sc.prim_count += 1
    # global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))

    global_sc.add_shader_module(func_name, 
        function_name=custom_func_name, 
        num_points=num_points
    )
    return global_sc

@rec_sdf_shader_eval.register
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
    global_sc = rec_sdf_shader_eval(inner_expr, global_sc=global_sc)

    pos3d = global_sc.local_sc.pos_stack.pop()
    sdf2d = global_sc.local_sc.res_sdf_stack.pop()
    sdf2d_type, sdf2d_name = sdf2d
    func_name = "ApplyHeight"
    height = _inline_parse_param_from_expr(plane, apply_height_expr.args[1:], global_sc)[0]
    sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    
    code_line = f"{sdf2d_type} {sdf_name} = {func_name}({pos3d}, {sdf2d_name}, {height});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    if sdf2d_type == "float":
        prim_name = f"prim_{global_sc.prim_count}"
        code_line = f"vec2 {prim_name} = vec2({sdf_name}, {global_sc.prim_count});"
        global_sc.local_sc.add_codeline(code_line)
        global_sc.prim_count += 1
        global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))
    else:
        global_sc.local_sc.res_sdf_stack.append((sdf2d_type, sdf_name))

    return global_sc


@rec_sdf_shader_eval.register
def eval_mxg_function(expression: ms.MarkerNode, global_sc:GlobalShaderContext=None):
    inner_expr = expression.args[0]
    global_sc = rec_sdf_shader_eval(inner_expr, global_sc=global_sc)
    return global_sc



def compile_shader(expression_dict, state_map, global_sc=None,
    mode="geom", geom_prefix=None) -> GlobalShaderContext:
    per_inst_motion_map = state_converter(state_map)
    main_lines = []
    master_sdf_counter = 0
    for ind, (geometry_name, expression) in enumerate(expression_dict.items()):
        if geometry_name in per_inst_motion_map:

            inst_transition_map = per_inst_motion_map[geometry_name]
            if geom_prefix is not None:
                geometry_name = f"{geom_prefix}_{geometry_name}"
            cur_expr_name = f"{geometry_name}SDF"
            global_sc.push_codebook(cur_expr_name, SCENE_EXPR_PROPS)
            if mode == "geom":
                global_sc = rec_sdf_shader_eval(expression, global_sc=global_sc)
            elif mode == "mat":
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

    min_global_step = min([v for v in state_map.keys()])
    max_global_step = max([v for v in state_map.keys()])
    global_sc.uniforms["globalStateStep"] = {
        "type": "float",
        "init_value": 0.0,
        'min': [min_global_step,],
        "max": [max_global_step,]
    }
    return global_sc


def compile_set_multipass(expression_dict, state_map, settings=None, 
                          return_shader_context=False,
                          post_process_shader=None) -> type_union[Tuple[List[Dict[str, Any]], List[GlobalShaderContext]], List[Dict[str, Any]]]:
    if settings is None:
        settings = {}
    all_shader_bundles = []
    all_global_sc = []


    render_mode = settings.get("render_mode", "v4")
    AA = settings.get("variables", {}).get("_AA", 1)

    global_sc = GlobalShaderContext()
    
    global_sc = compile_shader(expression_dict, state_map, global_sc=global_sc, mode="geom")
        
    global_sc.resolve_codebook()
    global_sc.add_shader_module("main_sdf_trace", AA=AA)
    
    shader_code = global_sc.emit_shader_code(settings, version="sdf_trace")

    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    
    cur_res = uniforms['resolution']['init_value']
    width = cur_res[0]  * AA
    height = cur_res[1] * AA
    
    # uniforms['resolution']['init_value'] = (width, height)

    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": textures,
        "input_FBOs": [],
        "output_FBO": {"name": "distance_travelled", "width": width, "height": height, "type": "vec2"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)

    # ================ SECOND PASS ================

    if render_mode in ["v3", "v4"]:
        global_sc = GlobalShaderContext()
        global_sc.push_codebook("GEOM_EXPRESSION", SCENE_EXPR_PROPS)
        global_sc = compile_shader(expression_dict, state_map, global_sc=global_sc, mode="geom", geom_prefix="geom")
        global_sc.resolve_codebook() # This will finins ahd add the function.
        global_sc.push_codebook("SCENE_EXPRESSION", SCENE_EXPR_PROPS)
        
    else:
        global_sc = GlobalShaderContext()

    global_sc = compile_shader(expression_dict, state_map, global_sc=global_sc, mode="mat")

    global_sc.resolve_codebook() 
    if render_mode in ["v3"]:
        global_sc.resolve_material_stack(version=render_mode)
    global_sc.add_shader_module(posttrace_map[render_mode], AA=AA)
    
    shader_code = global_sc.emit_shader_code(settings, version="post_sdf_trace")
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    
    cur_res = uniforms['resolution']['init_value']
    width_2 = cur_res[0] * AA
    height_2 = cur_res[1] * AA
    # uniforms['resolution']['init_value'] = (width_2, height_2)
    
    output_name = "intermediate_image"
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": textures,
        "input_FBOs": [{"name": "distance_travelled", "width": width, "height": height, "type": "vec2"}],
        "output_FBO": {"name": output_name, "width": width_2, "height": height_2, "type": "vec4"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)
    
    third_bundle, output_name = create_third_pass_shader_bundle(
        settings, width_2, height_2, output_name,
        post_process_shader=post_process_shader, AA=AA
    )
    all_shader_bundles.extend(third_bundle)

    # ================ FOURTH PASS (AA) ================
    aa_bundle = create_aa_pass_shader_bundle(width_2, height_2, AA, output_name)
    if aa_bundle:
        all_shader_bundles.append(aa_bundle)

    if return_shader_context:
        return all_shader_bundles, all_global_sc
    else:
        return all_shader_bundles