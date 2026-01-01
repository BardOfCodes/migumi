import numpy as np
import torch as th

import geolipi.symbolic as gls
import sympy as sp

VALID_REGION_PADDING = 0.2
PURTURBATION_RATE = 1e-4

def get_frame_from_normal(normal):
    plane_normal = normal / th.norm(normal, dim=-1, keepdim=True)  # Ensure normal is unit-length
    if th.abs(plane_normal[2]) < 0.999:
        arbitrary = th.tensor([0.0, 0.0, 1.0], dtype=th.float32, device=normal.device)
    else:
        arbitrary = th.tensor([1.0, 0.0, 0.0], dtype=th.float32, device=normal.device)

    x_axis = th.cross(arbitrary, plane_normal, dim=-1)
    x_axis = x_axis / th.norm(x_axis)
    y_axis = th.cross(plane_normal, x_axis, dim=-1)
    y_axis = y_axis / th.norm(y_axis)
    
    return x_axis, y_axis, normal
            
def get_frame_from_normal_np(normal):
    normal = normal / np.linalg.norm(normal)  # Ensure normal is unit-length

    # Choose a stable arbitrary vector for computing the new X-axis
    if abs(normal[2]) < 0.999:
        arbitrary = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        arbitrary = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    # Compute the new coordinate frame
    x_axis = np.cross(arbitrary, normal)
    x_axis /= np.linalg.norm(x_axis)  # Normalize

    y_axis = np.cross(normal, x_axis)
    y_axis /= np.linalg.norm(y_axis)  # Normalize
    return x_axis, y_axis, normal

            
            

def compute_plane_transform(origin, normal):
    """
    Compute a transformation matrix that rotates an object such that its local
    (0,1,0) "up" axis aligns with the given plane normal, and then shifts it to 
    the plane origin.

    Args:
        origin: (3,) array-like, the origin of the plane.
        normal: (3,) array-like, the normal of the plane.

    Returns:
        A 4x4 transformation matrix that first rotates and then translates the object.
    """
    normal = np.array(normal, dtype=np.float64)
    origin = np.array(origin, dtype=np.float64)
    x_axis, y_axis, z_axis = get_frame_from_normal_np(normal)

    # Construct the rotation matrix
    rotation_matrix = np.eye(4)
    rotation_matrix[:3, 0] = x_axis  # X-axis
    rotation_matrix[:3, 1] = y_axis  # Y-axis (mapped from (0,1,0))
    rotation_matrix[:3, 2] = z_axis  # Z-axis (mapped from plane normal)

    # Construct the translation matrix
    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = origin  # Apply translation after rotation

    # Final transformation: rotate first, then translate
    transform = translation_matrix @ rotation_matrix

    return transform





def get_projected_region_bounds_2d(plane, region_bbox_3d, sketcher_2d):
    """
    Given a plane and a 3D bounding box, return 2D bounds of its projection in plane-local coords.
    """
    min_3d, max_3d = region_bbox_3d
    corners = np.array([
        [min_3d[0], min_3d[1], min_3d[2]],
        [max_3d[0], min_3d[1], min_3d[2]],
        [max_3d[0], max_3d[1], min_3d[2]],
        [min_3d[0], max_3d[1], min_3d[2]],
        [min_3d[0], min_3d[1], max_3d[2]],
        [max_3d[0], min_3d[1], max_3d[2]],
        [max_3d[0], max_3d[1], max_3d[2]],
        [min_3d[0], max_3d[1], max_3d[2]],
    ])

    plane_origin = np.array([float(x) for x in plane.args[0]])
    plane_normal = np.array([float(x) for x in plane.args[1]])
    verts = corners - plane_origin

    verts = th.from_numpy(verts).to(sketcher_2d.device).float()
    plane_normal = th.tensor(plane_normal, dtype=th.float32, device=sketcher_2d.device)

    x_axis, y_axis, z_axis = get_frame_from_normal(plane_normal)
    
    coords_local = th.stack([
        (verts * x_axis).sum(-1),
        (verts * y_axis).sum(-1)
    ], dim=-1)

    min_xy = coords_local.min(0)[0].cpu().numpy()
    max_xy = coords_local.max(0)[0].cpu().numpy()
    return min_xy, max_xy



def reflect_expr_X(expr):
    # Reflect all points
    if isinstance(expr, gls.PolyArc2D):
        args = expr.args[0]
        new_args = []
        for arg in args:
            new_args.append((arg[0], -arg[1], -arg[2]))
        return gls.PolyArc2D(tuple(new_args))
    else:
        args = expr.args
        new_args = []
        for arg in args:
            if isinstance(arg, gls.GLFunction):
                new_args.append(reflect_expr_X(arg))
            else:
                new_args.append(arg)
        return type(expr)(*new_args)
def reflect_expr_Y(expr):
    # Reflect all points
    if isinstance(expr, gls.PolyArc2D):
        args = expr.args[0]
        new_args = []
        for arg in args:
            new_args.append((-arg[0], arg[1], -arg[2]))
        return gls.PolyArc2D(tuple(new_args))
    else:
        args = expr.args
        new_args = []
        for arg in args:
            if isinstance(arg, gls.GLFunction):
                new_args.append(reflect_expr_X(arg))
            else:
                new_args.append(arg)
        return type(expr)(*new_args)
    
    
def set_bounds_by_expr(expr, sketcher_2d):
    bounds_2d = get_expr_2d_bounds(expr)
    bounds_2d = np.array(bounds_2d)
    bounds_2d[0] -= VALID_REGION_PADDING
    bounds_2d[1] += VALID_REGION_PADDING

    scale = tuple((bounds_2d[1, i] - bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    origin = tuple((bounds_2d[1, i] + bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    sketcher_2d.adapt_coords(scale=scale, origin=origin)


def get_expr_bounds(expr, sketcher_2d):
    bounds_2d = get_expr_2d_bounds(expr)
    bounds_2d = np.array(bounds_2d)
    bounds_2d[0] -= VALID_REGION_PADDING
    bounds_2d[1] += VALID_REGION_PADDING

    scale = tuple((bounds_2d[1, i] - bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    origin = tuple((bounds_2d[1, i] + bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    return scale, origin

def get_bounds_by_expr(expr, sketcher_2d):
    bounds_2d = get_expr_2d_bounds(expr)
    bounds_2d = np.array(bounds_2d)
    bounds_2d[0] -= VALID_REGION_PADDING
    bounds_2d[1] += VALID_REGION_PADDING

    scale = tuple((bounds_2d[1, i] - bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    origin = tuple((bounds_2d[1, i] + bounds_2d[0, i]) / 2.0 for i in range(sketcher_2d.n_dims))
    return scale, origin

def get_expr_2d_bounds(expr):
    """
    Recursively computes the (min_x, min_y), (max_x, max_y) bounds of a 2D GLS expression.
    
    Args:
        expr: a gls.PolyArc2D or a composite expression (e.g., Union, Difference)
    
    Returns:
        min_xy: tuple (min_x, min_y)
        max_xy: tuple (max_x, max_y)
    """
    if isinstance(expr, gls.PolyArc2D):
        if isinstance(expr.args[0], sp.Symbol):
            points = expr.lookup_table[expr.args[0]].detach().cpu().numpy()
        else:
            points = expr.args[0]
        xs = [float(pt[0]) for pt in points]
        ys = [float(pt[1]) for pt in points]
        min_xy = (min(xs), min(ys))
        max_xy = (max(xs), max(ys))
        return min_xy, max_xy
    else:
        mins = []
        maxs = []
        for arg in expr.args:
            if isinstance(arg, gls.GLFunction):
                min_xy, max_xy = get_expr_2d_bounds(arg)
                if min_xy is None or max_xy is None:
                    continue
                mins.append(min_xy)
                maxs.append(max_xy)
            else:
                continue
        if len(mins) == 0:
            return None, None
        else:
            min_x = min(m[0] for m in mins)
            min_y = min(m[1] for m in mins)
            max_x = max(m[0] for m in maxs)
            max_y = max(m[1] for m in maxs)
            return (min_x, min_y), (max_x, max_y)
    

def apply_transform_to_expr(expr, transform):
    # Deals with only Tensors. 
    if isinstance(expr, gls.PolyArc2D):
        points = expr.args[0]
        points = np.array(points, dtype=np.float64)
        points_xy = points[:, :2]
        points_bulge = points[:, 2:3]
        if isinstance(transform, th.Tensor):
            points_xy = th.tensor(points_xy, dtype=th.float32, device=transform.device)
            points_homogeneous = th.cat([points_xy, th.ones(points_xy.shape[0], 1, device=transform.device)], dim=-1)
            new_points = points_homogeneous @ transform .T
            new_points = new_points[:, :2].cpu().numpy()
            mat_det = th.linalg.det(transform[:2, :2])
            if mat_det < 0:
                points_bulge = -points_bulge
        else:
            points_homogeneous = np.concatenate([points_xy, np.ones((points_xy.shape[0], 1))], axis=-1)
            new_points = points_homogeneous @ transform .T
            new_points = new_points[:, :2]
            mat_det = np.linalg.det(transform[:2, :2])
            if mat_det < 0:
                points_bulge = -points_bulge
        new_points = np.concatenate([new_points, points_bulge], axis=-1)
        new_points = new_points.tolist()
        new_points = tuple([(pt[0], pt[1], pt[2]) for pt in new_points])
        return gls.PolyArc2D(new_points)
    else:
        args = expr.args
        new_args = []
        for arg in args:
            if isinstance(arg, gls.GLFunction):
                new_args.append(apply_transform_to_expr(arg, transform))
            else:
                new_args.append(arg)
        return type(expr)(*new_args)
    

def convert_expr_basis(from_A, to_B, expr):
    R_2d_hom = get_transform_2d_orient(from_A, to_B)
    out_expr = apply_transform_to_expr(expr, R_2d_hom)
    return out_expr

def get_transform_2d_orient(from_A, to_B, to_tensor=True):
    
    cur_x, cur_y = from_A
    ref_x, ref_y = to_B
    if to_tensor:
        if not isinstance(cur_x, th.Tensor):
            cur_x = th.tensor(cur_x, dtype=th.float64, device="cuda")
            cur_y = th.tensor(cur_y, dtype=th.float64, device="cuda")
            ref_x = th.tensor(ref_x, dtype=th.float64, device="cuda")
            ref_y = th.tensor(ref_y, dtype=th.float64, device="cuda")
        
        A = th.stack([cur_x, cur_y], axis=1)  # shape (3, 2)
        B = th.stack([ref_x, ref_y], axis=1)  # shape (3, 2)
        R_2d = A.T @ B  # shape (2, 2)
        R_2d_hom = th.eye(3, 3, device=A.device)
    else:
        if isinstance(cur_x, th.Tensor):
            cur_x = cur_x.cpu().numpy()
            cur_y = cur_y.cpu().numpy()
            ref_x = ref_x.cpu().numpy()
            ref_y = ref_y.cpu().numpy()
        A = np.stack([cur_x, cur_y], 1)  # shape (3, 2)
        B = np.stack([ref_x, ref_y], 1)  # shape (3, 2)
        R_2d = A.T @ B  # shape (2, 2)
        R_2d_hom = np.eye(3, dtype=np.float64)
    R_2d_hom[:2, :2] = R_2d
    return R_2d_hom


def invert_bulge(expr):
    # Deals with only Tensors. 
    if isinstance(expr, gls.PolyArc2D):
        points = expr.args[0]
        points = np.array(points, dtype=np.float64)
        points_xy = points[:, :2]
        points_bulge = points[:, 2:3]
        new_points = np.concatenate([points_xy, -points_bulge], axis=-1)
        new_points = new_points.tolist()
        new_points = tuple([(pt[0], pt[1], pt[2]) for pt in new_points])
        return gls.PolyArc2D(new_points)
    else:
        args = expr.args
        new_args = []
        for arg in args:
            if isinstance(arg, gls.GLFunction):
                new_args.append(invert_bulge(arg))
            else:
                new_args.append(arg)
        return type(expr)(*new_args)

def perturb_expr(expr, rate=PURTURBATION_RATE):
    if isinstance(expr, gls.PolyArc2D):
        points = expr.args[0]
        points = np.array(points, dtype=np.float64)
        noise = np.random.uniform(-rate, rate, points[:, :2].shape)
        points[:, :2] += noise
        params = tuple([(x[0], x[1], x[2]) for x in points])
        return gls.PolyArc2D(params)
    else:
        new_expr_list = []
        for expr_arg in expr.args:
            if isinstance(expr_arg, gls.GLFunction):
                new_expr_list.append(perturb_expr(expr_arg, rate=rate))
            else:
                new_expr_list.append(expr_arg)
        return type(expr)(*new_expr_list)
    

def get_translation_vectors(origin, normal, origin_ref, normal_ref):
    
    ref_x, ref_y, ref_z = get_frame_from_normal_np(normal_ref)
    cur_x, cur_y, cur_z = get_frame_from_normal_np(normal)
    proj_origin = np.array((np.dot(origin_ref, ref_x).sum(), np.dot(origin_ref, ref_y).sum()), dtype=np.float64)
    other_origin = np.array((np.dot(origin, cur_x).sum(), np.dot(origin, cur_y).sum()), dtype=np.float64)
    # rotate it:
    A = np.stack([cur_x, cur_y], axis=1)  # shape (3, 2)
    B = np.stack([ref_x, ref_y], axis=1)  # shape (3, 2)
    R_2d = A.T @ B  # shape (2, 2)
    rotated_origin = other_origin @ R_2d  # shape (2,)
    
    planar_delta = rotated_origin - proj_origin
    # get delta along the normal
    normal_delta = (origin - origin_ref).dot(normal)
    
    return planar_delta, normal_delta

def set_sketcher_coords(opt_subtrs, active_part_timber, sketcher_2d):
    total_expr = []
    for part_name, timber_expr in active_part_timber.items():
        total_expr.append(timber_expr)
        for subtr_expr in opt_subtrs[part_name]:
            total_expr.append(subtr_expr)
    total_expr = gls.Union(*total_expr)
    set_bounds_by_expr(total_expr, sketcher_2d)