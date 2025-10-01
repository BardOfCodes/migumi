import geolipi.symbolic as gls
from collections import defaultdict

import migumi.symbolic as ms

def recursive_instmap_expr(expr, transformations=None):
    """
    Recursively flatten the expression tree to produce a per-part transformation expression.
    
    Args:
        expr: The input expression (Union, Translate3D, EulerRotate3D, or NamedGeometry).
        transformations: A list of accumulated transformations (initially None).

    Returns:
        A list of transformed expressions (e.g., Translate3D(NamedGeometry)).
    """
    if transformations is None:
        transformations = []

    # Handle different types of recursive_instmap_expr
    if isinstance(expr, gls.Union):
        # Flatten each sub-expression in the union
        flattened = []
        for sub_expr in expr.args:
            flattened.extend(recursive_instmap_expr(sub_expr, transformations))
        return flattened

    elif isinstance(expr, gls.Translate3D):
        # Add the translation to the transformation stack
        return recursive_instmap_expr(expr.args[0], transformations + [(0, expr.args[1])])

    elif isinstance(expr, gls.EulerRotate3D):
        # Add the rotation to the transformation stack
        return recursive_instmap_expr(expr.args[0], transformations + [(1, expr.args[1])])

    elif isinstance(expr, ms.NamedGeometry):
        # Apply all accumulated transformations to the NamedGeometry and return the result
        result = expr
        geometry_name = expr.args[0].name
        for transform, param in transformations:
            if transform == 0:
                result = gls.Translate3D(result, param)
            elif transform == 1:
                result = gls.EulerRotate3D(result, param)
        return [(result, geometry_name)]
    else:
        raise ValueError(f"Unsupported expression type: {type(expr)}")
    



def state_converter(state_map):
    """
    Go from (state -> State expr) map to
    (geometry_name -> (state_id -> instance_expr)) map.
    """
    instance_map = defaultdict(dict)
    for state_id, state_expr in state_map.items():
        instance_list = recursive_instmap_expr(state_expr)
        for instance_expr, geometry_name in instance_list:
            instance_map[geometry_name][state_id] = instance_expr
    return instance_map
