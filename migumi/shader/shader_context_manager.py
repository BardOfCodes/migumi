import os
import string

from .fragments.wrapper import template as fragment_template
from .compiler import recursive_convert_to_shader, generate_transition_code
from .state_based_converter import state_converter
from . import function_wrappers as fw # function_map, main_wrapper_template
from ordered_set import OrderedSet as OSet
FRAGMENT_RELATIVE_PATHS = [
    "./fragments/utils.frag.glsl",
    "./fragments/renderer.frag.glsl",
    "./fragments/camera.frag.glsl",
]

class ShaderContextManager:
    def __init__(self, config=None):
        # load all the base fragments
        self.fragment_template = string.Template(fragment_template)
        self.base_fragments = []
        # use cur file's base path
        base_path = os.path.dirname(os.path.abspath(__file__))
        for rel_path in FRAGMENT_RELATIVE_PATHS:
            with open(os.path.join(base_path, rel_path), "r") as f:
                self.base_fragments.append(f.read())

    def compile(self, expression_list):
        # compile the expression to shader code
        if not isinstance(expression_list, list):
            expression_list = [expression_list]
        fragments = []
        sdf_funcs = []
        final_lines = []
        all_uniforms = {}
        function_defs = OSet()
        custom_functions = []

        for ind, expression in enumerate(expression_list):
            shader_code_store = recursive_convert_to_shader(expression)
            function_defs.update(shader_code_store.tracked_functions)
            all_uniforms.update(shader_code_store.uniforms)
            code_list = shader_code_store.codebook
            code_lines = "\n".join(code_list)
            sdf_func_code = string.Template(fw.SDF_FUNCTION_WRAPPER)
            sdf_func_code = sdf_func_code.substitute({
                'code_lines': code_lines,
                'function_name': f"sdf_call_{ind}"
            })
            sdf_funcs.append(sdf_func_code)
            final_line = f"vec2 res_{ind} = sdf_call_{ind}(pos);"
            final_lines.append(final_line)
            custom_functions.extend(shader_code_store.custom_functions)

        functions = [getattr(fw, func) for func in function_defs] + custom_functions
        functions.extend(sdf_funcs)

        functions = "\n".join(functions)

        n_results = len(sdf_funcs)
        if n_results > 1:
            res_list = [f"res_{i}" for i in range(n_results)]
            res_list = ", ".join(res_list)
            final_line = f"res = MinRes({res_list});"
            # final_line = f"vec2 res = res_1;"
            final_lines.append(final_line)
        else:
            final_lines.append(f"res = res_0;")
        code_lines = "\n".join(final_lines)
        shader_code_store.uniforms = all_uniforms
        new_frag = string.Template(fw.MAIN_WRAPPER_TEMPLATE).substitute({
            "uniform_initialization": shader_code_store.convert_uniforms(),
            "function_definitions": functions,
            "code_lines": code_lines
        })
        print(shader_code_store.convert_uniforms())
        fragments.append(new_frag)

        # base_path = os.path.dirname(os.path.abspath(__file__))
        # with open(os.path.join(base_path, "./fragments/dummy.frag.glsl"), "r") as f:
        #     new_frag = f.read()
        # fragments.append(new_frag)
        fragments.insert(0, self.base_fragments[0])
        for fragment in self.base_fragments[1:]:
            fragments.append(fragment)

        # TEMPORARY

        code = "\n".join(fragments)
        substitute_dict = {
            "INNER_CODE": code,
        }
        shader_code = self.fragment_template.substitute(substitute_dict)

        uniform_dict = all_uniforms
        return shader_code, uniform_dict
    

    def compile_set(self, expression_dict, state_map, part_wise=False):
        # compile the expression to shader code
        fragments = []

        per_inst_motion_map = state_converter(state_map)
        shader_code_store = None
        main_lines = []
        master_sdf_counter = 0
        for ind, (geometry_name, (expression, bbox)) in enumerate(expression_dict.items()):
            if geometry_name in per_inst_motion_map:
                shader_code_store = recursive_convert_to_shader(expression, shader_code_store=shader_code_store)
                sdf_func_code = shader_code_store.convert_to_sdf_function(f"{geometry_name}SDF")
                shader_code_store.custom_functions.append(sdf_func_code)
                shader_code_store.refresh()
                ## Process the bbox
                shader_code_store.add_bbox(bbox, geometry_name)
                ## Process geometry
                shader_code_store.refresh()
                inst_transition_map = per_inst_motion_map[geometry_name]
                beta_mode = len(bbox) == 2
                shader_code_store = generate_transition_code(geometry_name, inst_transition_map, shader_code_store, beta_mode)
                shader_code_store.refresh()

                main_line = f"vec2 res_{master_sdf_counter} = {geometry_name}Stateful(pos, globalStateStep);"
                main_lines.append(main_line)
                master_sdf_counter += 1
        n_results = len(main_lines)
        main_code = process_main_code(main_lines, n_results)

        functions = [getattr(fw, func) for func in shader_code_store.tracked_functions] + shader_code_store.custom_functions
        functions = "\n".join(functions)

        min_global_step = min([v for v in state_map.keys()])
        max_global_step = max([v for v in state_map.keys()])
        shader_code_store.uniforms["globalStateStep"] = {
            "type": "float",
            "init_value": 0.0,
            'min': [min_global_step,],
            "max": [max_global_step,]
        }
        uniforms = shader_code_store.convert_uniforms()
        # Get the Uniform from state Function.
        new_frag = string.Template(fw.MAIN_WRAPPER_TEMPLATE).substitute({
            "uniform_initialization": uniforms,
            "function_definitions": functions,
            "main_code": main_code
        })
        fragments.append(new_frag)

        # base_path = os.path.dirname(os.path.abspath(__file__))
        # with open(os.path.join(base_path, "./fragments/dummy.frag.glsl"), "r") as f:
        #     new_frag = f.read()
        # fragments.append(new_frag)
        fragments.insert(0, self.base_fragments[0])
        for fragment in self.base_fragments[1:]:
            fragments.append(fragment)

        # TEMPORARY

        code = "\n".join(fragments)
        substitute_dict = {
            "INNER_CODE": code,
        }
        shader_code = self.fragment_template.substitute(substitute_dict)

        uniform_dict = shader_code_store.uniforms
        return shader_code, uniform_dict
    
def process_main_code(final_lines, n_results):
    if n_results > 1:
        res_list = [f"res_{i}" for i in range(n_results)]
        res_list = ", ".join(res_list)
        final_line = f"res = MinRes({res_list});"
        final_lines.append(final_line)
    else:
        final_lines.append(f"res = res_0;")
    code_lines = "\n".join(final_lines)
    return code_lines
