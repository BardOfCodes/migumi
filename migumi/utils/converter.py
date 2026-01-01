import asmblr.nodes as anodes
import geolipi.symbolic as gls
import migumi.symbolic as ms
import sysl.symbolic as sls
import distinctipy

BOX_THRESH = 0.1

def fix_format(data):

    diff_ids = []
    for node in data['nodes']:
        if node['name'] == "Plane3D":
            node['name'] = "PlaneV23D"
        elif node['name'] == "Translate3D":
            if "param" in node['data']:
                node['data'] = {"offset": node['data']['param']}
        elif node['name'] == "Translate2D":
            if "param" in node['data']:
                node['data'] = {"offset": node['data']['param']}
        elif node['name'] == "EulerRotate2D":
            if "param" in node['data']:
                node['data'] = {"angle": node['data']['param']}
        elif node['name'] == "EulerRotate3D":
            if "param" in node['data']:
                node['data'] = {"angles": node['data']['param']}
        elif node['name'] == "Difference":
            diff_ids.append(node['id'])

    for conn in data['connections']:
        if conn['target'] in diff_ids:
            cur_output = conn['targetInput']
            if cur_output == "expr1":
                conn['targetInput'] = "expr_0"
            elif cur_output == "expr2":
                conn['targetInput'] = "expr_1"
    return data


def get_expr_and_state(nodes):

    expr_dict = {}
    state_map = {}
    for node in nodes:
        if isinstance(node, anodes.RegisterGeometry):
            # modify expr so that the "translations beyond "set Material are not included"
            outputs = node.evaluate(None)
            expr = outputs['expr']
            bbox = outputs['bbox']
            expr_name = outputs['name']
            expr_dict[expr_name] = (expr, bbox)
        elif isinstance(node, anodes.RegisterState):
            outputs = node.evaluate(None)
            expr = outputs['expr']
            state = outputs['state'][0]
            state_map[state] = expr
        else:
            pass
            # raise ValueError("Invalid Node Type")
    # sort by keys
    state_sequence = sorted(state_map.keys())
    state_map = {state: state_map[state] for state in state_sequence}
    return expr_dict, state_map

def fix_expr_dict(expression_dict, mode="v1", add_bounding=True):
    n_expressions = len(expression_dict)
    colors = distinctipy.get_colors(n_expressions)
    colors = [tuple(color) for color in colors]
    for ind, (geometry_name, (expression, bbox)) in enumerate(expression_dict.items()):
        bbox_expr = gls.Box3D(bbox)
        expression = fix_expression_v2(expression, colors[ind], mode)
        if add_bounding:
            bounded_expression = sls.BoundedSolid(expression, bbox_expr, (BOX_THRESH,))
        else:
            bounded_expression = expression
        expression_dict[geometry_name] = bounded_expression
    return expression_dict

def fix_expression_v2(gls_expr, color, mode="v1"):
    if isinstance(gls_expr, ms.SetMaterial):
        new_args = []
        material_id = gls_expr.args[1]
        inner_expr = fix_expression_v2(gls_expr.args[0], color, mode)
        if mode == "v1":
            new_expression = sls.MatSolidV1(inner_expr, sls.MaterialV1(material_id))
        elif mode == "v2":
            new_expression = sls.MatSolidV2(inner_expr, sls.MaterialV2(color))
        elif mode == "v3":
            mat_expr = sls.NonEmissiveMaterialV3(color, (0.0,), (0.9,), (0.9,))
            new_expression = sls.MatSolidV3(inner_expr, mat_expr)
        elif mode == "v4":
            mat_expr = sls.MaterialV4(color, (0.0, 0.0,0.0), (0.2, 0.1, 0.9,))
            new_expression = sls.MatSolidV4(inner_expr, mat_expr)
        else:
            raise ValueError(f"Invalid mode: {mode}")
        return new_expression
    else:
        if isinstance(gls_expr, gls.GLFunction):
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr = fix_expression_v2(arg, color, mode)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args)
        else:
            return gls_expr
