

Rotate3D = """
vec3 Rotate3D( vec3 p, vec3 angles )
{
    float cx = cos(angles.x), sx = sin(angles.x);
    float cy = cos(angles.y), sy = sin(angles.y);
    float cz = cos(angles.z), sz = sin(angles.z);
    mat3 rx = mat3(1.0, 0.0, 0.0, 0.0, cx, -sx, 0.0, sx, cx);
    mat3 ry = mat3(cy, 0.0, sy, 0.0, 1.0, 0.0, -sy, 0.0, cy);
    mat3 rz = mat3(cz, -sz, 0.0, sz, cz, 0.0, 0.0, 0.0, 1.0);
    return rz * ry * rx * p;
}
"""

Rotate2D = """
vec2 Rotate2D( in vec2 p, in float angle )
{
    float s = sin(-angle);
    float c = cos(-angle);
    mat2 m = mat2(c, -s, s, c);
    return m * p;
}
"""

Union = """
float Union( float d1)
{
    return d1;
}
float Union( float d1, float d2 )
{
	return (d1<d2) ? d1 : d2;
}
float Union( float d1, float d2 , float d3)
{
    return Union(Union(d1, d2), d3);
}
float Union( float d1, float d2 , float d3, float d4)
{
    return Union(Union(d1, d2), Union(d3, d4));
}
float Union( float d1, float d2 , float d3, float d4, float d5)
{
    return Union(Union(d1, d2), Union(d3, d4, d5));
}
float Union( float d1, float d2 , float d3, float d4, float d5, float d6)
{
    return Union(Union(d1, d2), Union(d3, d4, d5, d6));
}
float Union( float d1, float d2 , float d3, float d4, float d5, float d6, float d7)
{
    return Union(Union(d1, d2), Union(d3, d4, d5, d6, d7));
}
float Union( float d1, float d2 , float d3, float d4, float d5, float d6, float d7, float d8)
{
    return Union(Union(d1, d2), Union(d3, d4, d5, d6, d7, d8));
}
"""

Intersection = """
float Intersection( float d1, float d2 )
{
	return (d1 > d2) ? d1 : d2;
}
float Intersection( float d1, float d2 , float d3)
{
    return Intersection(Intersection(d1, d2), d3);
}
float Intersection( float d1, float d2 , float d3, float d4)
{
    return Intersection(Intersection(d1, d2), Intersection(d3, d4));
}
float Intersection( float d1, float d2 , float d3, float d4, float d5)
{
    return Intersection(Intersection(d1, d2), Intersection(d3, d4, d5));
}
float Intersection( float d1, float d2 , float d3, float d4, float d5, float d6)
{
    return Intersection(Intersection(d1, d2), Intersection(d3, d4, d5, d6));
}
float Intersection( float d1, float d2 , float d3, float d4, float d5, float d6, float d7)
{
    return Intersection(Intersection(d1, d2), Intersection(d3, d4, d5, d6, d7));
}
float Intersection( float d1, float d2 , float d3, float d4, float d5, float d6, float d7, float d8)
{
    return Intersection(Intersection(d1, d2), Intersection(d3, d4, d5, d6, d7, d8));
}
"""

Difference = """
float Difference( float d1, float d2 )
{
    return (d1>-d2) ? d1 : -d2;
}
"""


Box3D = """
float Box3D( vec3 p, vec3 b )
{
    vec3 size = b / 2.0;
    vec3 d = abs(p) - size;
    return min(max(d.x,max(d.y,d.z)),0.0) + length(max(d,0.0));
}
"""

OBox3D = """
float OBox3D( vec3 p, vec3 scale, vec3 origin )
{
    vec3 size = scale / 2.0;
    vec3 d = abs(p - origin) - size;
    return min(max(d.x,max(d.y,d.z)),0.0) + length(max(d,0.0));
}
"""

BoundingBox3D = """
float BoundingBox3D( vec3 p, vec3 b )
{
    vec3 q = abs(p) - b;
    return length(max(q, 0.0));
}
"""

Sphere3D = """
float Sphere3D( vec3 p, float s )
{
    return length(p)-s;
}
"""

Circle2D = """
float Circle2D( vec2 p, float s )
{
    return length(p)-s;
}
"""

iBox = """
vec2 iBox( in vec3 ro, in vec3 rd, in vec3 rad ) 
{
    vec3 m = 1.0/rd;
    vec3 n = m*ro;
    vec3 k = abs(m)*rad;
    vec3 t1 = -n - k;
    vec3 t2 = -n + k;
	return vec2( max( max( t1.x, t1.y ), t1.z ),
	             min( min( t2.x, t2.y ), t2.z ) );
}
"""

Rectangle2D = """
float Rectangle2D( in vec2 p, in vec2 b )
{   
    vec2 size = b / 2.0;
    vec2 d = abs(p)-size;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}
"""

Trapezoid2D = """
float Trapezoid2D( in vec2 p, in float r1, float r2, float he )
{
    vec2 k1 = vec2(r2,he);
    vec2 k2 = vec2(r2-r1,2.0*he);
    p.x = abs(p.x);
    vec2 ca = vec2(p.x-min(p.x,(p.y<0.0)?r1:r2), abs(p.y)-he);
    vec2 cb = p - k1 + k2*clamp( dot(k1-p,k2)/dot2(k2), 0.0, 1.0 );
    float s = (cb.x<0.0 && ca.y<0.0) ? -1.0 : 1.0;
    return s*sqrt( min(dot2(ca),dot2(cb)) );
}
"""

LocalHFCoord = """
vec3 LocalHFCoord(vec3 p, vec3 plane_origin, vec3 plane_normal) {
    // Normalize the plane normal
    plane_normal = plane_normal / length(plane_normal);

    // Shift the point to the local coordinate system of the plane
    p = p - plane_origin;

    // Compute a robust x_axis
    vec3 arbitrary = abs(plane_normal.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 x_axis = normalize(cross(arbitrary, plane_normal));

    // Compute the y_axis
    vec3 y_axis = normalize(cross(plane_normal, x_axis));

    // Project the point into the local coordinate system
    vec3 local_p = vec3(dot(p, x_axis), dot(p, y_axis), dot(p, plane_normal));
    return local_p;
}
"""


BBoxedLocalHFCoord = """
vec3 BBoxedLocalHFCoord(vec3 p, vec3 plane_origin, vec3 plane_normal, vec3 bbox_scale, vec3 bbox_origin) {
    // Normalize the plane normal
    vec3 size = bbox_scale / 2.0;
    vec3 d = abs(p - bbox_origin) - size;
    float bbox_sdf = min(max(d.x,max(d.y,d.z)),0.0) + length(max(d,0.0));
    vec3 local_p = p;
    if (bbox_sdf < 0.2) {
        plane_normal = plane_normal / length(plane_normal);

        // Shift the point to the local coordinate system of the plane
        p = p - plane_origin;

        // Compute a robust x_axis
        vec3 arbitrary = abs(plane_normal.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
        vec3 x_axis = normalize(cross(arbitrary, plane_normal));

        // Compute the y_axis
        vec3 y_axis = normalize(cross(plane_normal, x_axis));

        // Project the point into the local coordinate system
        vec3 local_p = vec3(dot(p, x_axis), dot(p, y_axis), dot(p, plane_normal));
    }
    return local_p;
}
"""

ApplyHeight = """
float ApplyHeight( vec3 p, float sdf2d, float height )
{   

    vec2 d = vec2(sdf2d, max(p.z - height, -p.z));
    return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}
"""


BBoxedApplyHeight = """
float BBoxedApplyHeight( vec3 p, float sdf2d, float height , vec2 )
{   

    vec2 d = vec2(sdf2d, max(p.z - height, -p.z));
    return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}
"""

SetMaterial = """
vec2 SetMaterial( float sdf2d, float material_id )
{   
    vec2 res = vec2( sdf2d, material_id );
    return res;
}
"""

MaskableSetMaterial = """
uniform bool ${bool_name};
vec2 ${name}( float sdf2d, float material_id )
{   
    vec2 res = vec2( sdf2d, material_id );
    if (!${bool_name}){
        res = vec2( 100.0, -1.0 );
    }
    return res;
}
"""



MinRes = """
vec2 MinRes( vec2 a, vec2 b )
{
    return (a.x<b.x) ? a : b;
}
vec2 MinRes( vec2 a, vec2 b , vec2 c)
{
    return MinRes(MinRes(a, b), c);
}
vec2 MinRes( vec2 a, vec2 b , vec2 c, vec2 d)
{
    return MinRes(MinRes(a, b), MinRes(c, d));
}

vec2 MinRes( vec2 a, vec2 b , vec2 c, vec2 d, vec2 e)
{
    return MinRes(MinRes(a, b), MinRes(c, d, e));
}

vec2 MinRes( vec2 a, vec2 b , vec2 c, vec2 d, vec2 e, vec2 f)
{
    return MinRes(MinRes(a, b), MinRes(c, d, e, f));
}
vec2 MinRes( vec2 a, vec2 b , vec2 c, vec2 d, vec2 e, vec2 f, vec2 g)
{
    return MinRes(MinRes(a, b), MinRes(c, d, e, f, g));
}


"""

PolyArc2D = """
vec2 sdLine( in vec2 p, in vec2 a, in vec2 b )
{
	vec2 pa = p-a, ba = b-a;
	float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
    float d = dot2(pa-ba*h);
    bvec3 cond = bvec3( p.y>=a.y, p.y<b.y, cro(ba, pa)>0.0);
    float s = ( all(cond) || all(not(cond)) )? -1.0: 1.0;
    return vec2(d, s);
}

float sdArc( in vec2 p, in vec2 sc, in float ra )
{
    // sc is the sin/cos of the arc's aperture
    p.x = abs(p.x);
    vec2 d = sc.x < 0.0 ? -sc * ra : sc * ra;
    return ((sc.y*p.x>sc.x*p.y) ? length(p-d) : 
                                  abs(length(p)-ra));
}
vec2 sinCosFromHalfTan(float tanHalfX)
{
    float tanHalfSq = tanHalfX * tanHalfX;
    float denom = 1.0 + tanHalfSq;
    return vec2((2.0 * tanHalfX) / denom, (1.0 - tanHalfSq) / denom);
}
float angleFromOrigin(vec2 v) {
    float angle = atan(v.y, v.x); // Get angle in radians (range: -PI to PI)
    return angle < 0.0 ? angle + 6.28318530718 : angle; // Convert to range [0, 2PI]
}

float maxElement(vec4 v) {
    return max(max(v.x, v.y), max(v.z, v.w));
}

vec2 sdBulgeArc(in vec2 p, in vec2 a, in vec2 b, in float bulge)
{
    vec2 ba = b - a;
    float l = length(ba); // Chord length

    // Compute the orthogonal vector and center
    vec2 ortho_ba = normalize(vec2(ba.y, -ba.x));
    float tan_tby2 = 2.0 * bulge / (1.0 - bulge * bulge);
    float h = l / (2.0 * tan_tby2);
    vec2 center = (a + b) * 0.5 + ortho_ba * h;

    // Rotate point and endpoints to align arc with x-axis
    float theta = atan(ba.y, ba.x);
    float cosTheta = cos(-theta);
    float sinTheta = sin(-theta);
    mat2 rotationMatrix = mat2(cosTheta, sinTheta, -sinTheta, cosTheta);
    vec2 relative_p = p - center;
    vec2 rotPoint = rotationMatrix * relative_p;

    // Compute signed distance and winding number condition
    float radius = length(a - center);
    vec2 sc = sinCosFromHalfTan(bulge);

    // Compute signed distance
    float d = sdArc(rotPoint, sc, radius);
    
    float wn = 1.;
    
    float minY = min(a.y, b.y);
    float maxY = max(a.y, b.y);
    bool inRange = (p.y > minY && p.y < maxY);
    bool in_circ = length(relative_p) <= radius;
    
    
    if (inRange)
    {
        vec2 pa = p - a;
        bvec3 cond = bvec3( p.y>=a.y, p.y <b.y, cro(ba, pa) > 0.0);
        bool left_ba = all(cond) || all(not(cond));
        bool positive_arc = (b.y >= a.y && bulge > 0.0) || (b.y < a.y && bulge < 0.0)  ;
        if (positive_arc)
        {
            wn *= (left_ba && (!in_circ))? -1. : 1.0;   
        }
        else{
            wn *= (left_ba || (in_circ))? -1. : 1.0;   
        }
     }
     else{
        // Need to figure out chord min and max and if its within that then the other condition applies. 
        vec4 consider = vec4(a.y, b.y, a.y, b.y);
        float maxy = center.y + radius;
        float miny = center.y - radius;
        vec2 ac = a - center;
        vec2 bc = b - center;
        vec2 start = ac;
        vec2 end = bc;
        if (bulge >=0.0){
            start = bc;
            end = ac;
        }
        // for up
        float c = cro(start, end);
        float c1 = -start.x;
        float c2 = -end.x;
        consider[2] = (c > 0.0)
            ? c1 < 0.0 && c2 > 0.0 ? maxy : a.y
            : c1 < 0.0 || c2 > 0.0 ? maxy : a.y;
        c1 = start.x;
        c2 = end.x; 
        consider[3] = (c > 0.0)
            ? c1 < 0.0 && c2 > 0.0 ? miny: a.y
            : c1 < 0.0 || c2 > 0.0 ? miny : a.y;

        float arc_max_y = maxElement(consider);
        float arc_min_y = -maxElement(-consider);
        bool in_arc_range = p.y > arc_min_y && p.y < arc_max_y;
        wn *= (in_circ && in_arc_range)? -1.: 1.0;
      }
    return vec2(d*d, wn);
}
"""

PolyArc2DInner = """
float ${name}( in vec2 p, in vec3[${n_points}] v )
{
    // do this only if the bbox is entered. 
    
    vec2 a = vec2(v[0].x, v[0].y);
    vec2 b = vec2(v[1].x, v[1].y);
    float d = 100.0; // dot(p-a,p-a);
    float s = 1.0;
    vec2 ds = vec2(d, s);
    for( int i=0;i<${n_points}; i++ )
    {
        // distance
        a = vec2(v[i].x, v[i].y);
        int next = (i+1)%${n_points};
        b = vec2(v[next].x, v[next].y);
        if (v[i].z == 0.0){
            ds = sdLine(p, a, b);
        }else{
            ds = sdBulgeArc(p, a, b, -v[i].z);
        }
        d = min(d, ds.x);
        s *= ds.y;
    }
    return s*sqrt(d);
}
"""

#### Helper for Transition

Slerp = """
vec4 slerp(vec4 q0, vec4 q1, float alpha) {
    // Compute the dot product (cosine of the angle between q0 and q1)
    float dotProduct = dot(q0, q1);

    // Ensure the shortest path is taken
    if (dotProduct < 0.0) {
        q1 = -q1;
        dotProduct = -dotProduct;
    }

    // Use linear interpolation if the angle is very small
    float epsilon = 1e-6;
    if (dotProduct > 1.0 - epsilon) {
        return normalize(mix(q0, q1, alpha));
    }

    // Compute the angle (theta)
    float theta = acos(dotProduct);
    float sinTheta = sin(theta);

    // Interpolate
    float scale0 = sin((1.0 - alpha) * theta) / sinTheta;
    float scale1 = sin(alpha * theta) / sinTheta;

    return normalize(scale0 * q0 + scale1 * q1);
}
"""


TranslationMatrix = """
mat4 TranslationMatrix(vec3 translation) {
    mat4 result = mat4(1.0); // Identity matrix
    result[3] = vec4(translation, 1.0); // Set the translation column
    return result;
}
"""
QuatRotationMatrix = """
mat4 QuatRotationMatrix(vec4 quaternion) {
    float x = quaternion.x;
    float y = quaternion.y;
    float z = quaternion.z;
    float w = quaternion.w;

    float x2 = x + x, y2 = y + y, z2 = z + z;
    float xx = x * x2, yy = y * y2, zz = z * z2;
    float xy = x * y2, xz = x * z2, yz = y * z2;
    float wx = w * x2, wy = w * y2, wz = w * z2;

    mat4 result = mat4(1.0); // Identity matrix
    result[0][0] = 1.0 - (yy + zz);
    result[0][1] = xy - wz;
    result[0][2] = xz + wy;

    result[1][0] = xy + wz;
    result[1][1] = 1.0 - (xx + zz);
    result[1][2] = yz - wx;

    result[2][0] = xz - wy;
    result[2][1] = yz + wx;
    result[2][2] = 1.0 - (xx + yy);

    return result;
}
"""
EulerRotationMatrix = """
mat4 EulerRotationMatrix(vec3 rotation) {
    // Extract individual angles
    float rx = rotation.x; // Rotation around X-axis
    float ry = rotation.y; // Rotation around Y-axis
    float rz = rotation.z; // Rotation around Z-axis

    // Compute sines and cosines of angles
    float cx = cos(rx), sx = sin(rx);
    float cy = cos(ry), sy = sin(ry);
    float cz = cos(rz), sz = sin(rz);

    // Rotation matrix components
    mat3 R_x = mat3(
        1.0,  0.0,  0.0,
        0.0,  cx,  -sx,
        0.0,  sx,   cx
    );

    mat3 R_y = mat3(
         cy,  0.0,  sy,
         0.0,  1.0,  0.0,
        -sy,  0.0,  cy
    );

    mat3 R_z = mat3(
        cz, -sz,  0.0,
        sz,  cz,  0.0,
        0.0, 0.0,  1.0
    );

    // Combine the rotations: R = Rz * Ry * Rx
    mat3 R = R_z * R_y * R_x;

    // Embed into a 4x4 matrix
    mat4 result = mat4(1.0); // Identity matrix
    result[0].xyz = R[0];    // Set top row
    result[1].xyz = R[1];    // Set middle row
    result[2].xyz = R[2];    // Set bottom row

    return result;
}
"""
RotationFromMatrix = """
vec4 RotationFromMatrix(mat4 mat) {
    float trace = mat[0][0] + mat[1][1] + mat[2][2];
    vec4 quaternion;

    if (trace > 0.0) {
        float s = sqrt(trace + 1.0) * 2.0;
        quaternion.w = 0.25 * s;
        quaternion.x = (mat[2][1] - mat[1][2]) / s;
        quaternion.y = (mat[0][2] - mat[2][0]) / s;
        quaternion.z = (mat[1][0] - mat[0][1]) / s;
    } else if ((mat[0][0] > mat[1][1]) && (mat[0][0] > mat[2][2])) {
        float s = sqrt(1.0 + mat[0][0] - mat[1][1] - mat[2][2]) * 2.0;
        quaternion.w = (mat[2][1] - mat[1][2]) / s;
        quaternion.x = 0.25 * s;
        quaternion.y = (mat[0][1] + mat[1][0]) / s;
        quaternion.z = (mat[0][2] + mat[2][0]) / s;
    } else if (mat[1][1] > mat[2][2]) {
        float s = sqrt(1.0 + mat[1][1] - mat[0][0] - mat[2][2]) * 2.0;
        quaternion.w = (mat[0][2] - mat[2][0]) / s;
        quaternion.x = (mat[0][1] + mat[1][0]) / s;
        quaternion.y = 0.25 * s;
        quaternion.z = (mat[1][2] + mat[2][1]) / s;
    } else {
        float s = sqrt(1.0 + mat[2][2] - mat[0][0] - mat[1][1]) * 2.0;
        quaternion.w = (mat[1][0] - mat[0][1]) / s;
        quaternion.x = (mat[0][2] + mat[2][0]) / s;
        quaternion.y = (mat[1][2] + mat[2][1]) / s;
        quaternion.z = 0.25 * s;
    }
    return normalize(quaternion);
}
"""
InterpAffine = """
mat4 InterpAffine(mat4 matA, mat4 matB, float alpha) {
    // Extract translation
    vec3 tA = vec3(matA[3].xyz); // Last column
    vec3 tB = vec3(matB[3].xyz);
    vec3 tInterp = mix(tA, tB, alpha);

    // Extract rotation (convert to quaternions)
    vec4 qA = RotationFromMatrix(matA);
    vec4 qB = RotationFromMatrix(matB);
    vec4 qInterp = slerp(qA, qB, alpha);

    // Construct the interpolated matrix
    mat4 result = mat4(1.0);
    result *= QuatRotationMatrix(qInterp); // Apply interpolated rotation
    result[3] = vec4(tInterp, 1.0); // Apply interpolated translation
    return result;
}
"""

ApplyAffine = """
vec3 ApplyAffine(mat4 affineMatrix, vec3 position) {
    // Convert vec3 to vec4 with homogeneous coordinates
    vec4 pos4D = vec4(position, 1.0);

    // Apply the affine transformation
    vec4 transformedPos = affineMatrix * pos4D;

    // Return the resulting vec3
    return transformedPos.xyz;
}
"""

SuperPrimitive3D = """

vec4 dSet(  float a ) { return vec4( a, 0.0, 0.0, 0.0 ); }
vec4 dSetX( float a ) { return vec4( a, 1.0, 0.0, 0.0 ); }
vec4 dSetY( float a ) { return vec4( a, 0.0, 1.0, 0.0 ); }
vec4 dSetZ( float a ) { return vec4( a, 0.0, 0.0, 1.0 ); }
vec4 dSqr(  vec4  a ) { return vec4( a.x*a.x, 2.0*a.x*a.yzw ); }
vec4 dMul(  vec4  a, vec4 b ) { return vec4( a.x*b.x, a.x*b.yzw + a.yzw*b.x ); }
vec4 dSqrt( vec4  v ) { float s = sqrt(v.x); return vec4( s, 0.5*v.yzw/s ); }
//vec4 dAbs( vec4 v ) { return vec4(abs(v.x), (v.x>0.0)?v.yzw:-v.yzw ); }
vec4 dAbs(  vec4  v ) { return (v.x>0.0)?v:-v; }
vec4 dMin(  vec4  a, float b ) { return (a.x<b) ? a : vec4(b,0.0,0.0,0.0); }
vec4 dMax(  vec4  a, float b ) { return (a.x>b) ? a : vec4(b,0.0,0.0,0.0); }
vec4 dMin(  vec4  a, vec4  b ) { return (a.x<b.x) ? a : b; }
vec4 dMax(  vec4  a, vec4  b ) { return (a.x>b.x) ? a : b; }

vec4 dLength( vec4 x, vec4 y, vec4 z ) { return dSqrt( dSqr(x) + dSqr(y) + dSqr(z) ); }
vec4 dLength( vec4 x, vec4 y ) { return dSqrt( dSqr(x) + dSqr(y)); }



vec3 revolve( in vec3 q, float offset, float rotate)
{
    q.xz = vec2(length(q.xy)-offset,q.z); 
    q.xz = mat2(cos(rotate),sin(rotate),-sin(rotate),cos(rotate)) * q.xz;
    return q;
}

struct Shape
{
    //----------------------------------------------------------------------
    // 2D shape                 // this block of fields is primitive specific
    //----------------------------------------------------------------------
    float width;                // width
    float height;               // height
    float corner0;              // corner 0 rounding amount
    float corner1;              // corner 1 rounding amount
    float corner2;              // corner 2 rounding amount
    float corner3;              // corner r 3ounding amount
    //----------------------------------------------------------------------
    // 2D global params         // this is common to all primitives
    //----------------------------------------------------------------------
    float thickness;            // it opens a hole in the 2D shape
    //----------------------------------------------------------------------
    // 2D to 3D.                // common to all prims. It's a revolution or extrussion
    //----------------------------------------------------------------------
    int   mode;                 // 0 = extrussion, 1 = revolution
    float extrussion;           // if revolution, this is unused
    float extrussionCorner1;    // if revolution, this offsets the 2D profile
    float extrussionCorner2;    // if revolution, this rotates the 2D profile
    //----------------------------------------------------------------------
    // 3D modifier
    //----------------------------------------------------------------------
    float onion;                // converts the solid to a shell of thickiness "onion" units
    float inflate;              // inflates the shape (with rounded/eucliedan corners) by "inflate" units
};

vec4 dfBox( vec4 px, vec4 py, vec2 b, vec4 r )
{

//vec3 dd = sdgBox(vec2(x.x,y.x), b, r );return vec4(dd.x, dd.y, 0.0, dd.z );
    r.xy = (px.x>0.0)?r.xy : r.zw;
    r.x  = (py.x>0.0)?r.x  : r.y;

    vec4 qx = dAbs(px) - dSet(b.x) + dSet(r.x);
    vec4 qy = dAbs(py) - dSet(b.y) + dSet(r.x);

    vec4 d = dMax(qx,qy);
    if( d.x>0.0 ) d = dLength( dMax(qx,0.0), dMax(qy,0.0) );
    
    return d - dSet(r.x);
}


// --- 2D to 3D ---

vec4 extrude( in vec4 d, vec4 z, in float h, float r )
{
    vec4 qx = d + dSet(r);
    vec4 qy = dAbs(z) - dSet(h);
    
    vec4 d1 = dMin(dMax(qx,qy),0.0);
    vec4 d2 = dLength( dMax(qx,0.0), dMax(qy,0.0) );
    return d1 + d2 - dSet(r);
}

vec4 sdShape( vec4 x, vec4 y, vec4 z, in Shape shape )
{
    // 2D shape
    vec4 d = dfBox( x, z, vec2(shape.width,shape.height), vec4(shape.corner0,shape.corner1,shape.corner2,shape.corner3) );

    // hole
    {
        float th = max(shape.extrussionCorner1,shape.extrussionCorner2)*0.5 + min(shape.width,shape.height)*0.5 - shape.thickness;
        d = dAbs(d+dSet(th)) - dSet(th);
    }

    // extrude (if not, this is just a 2D SDF), great for painting!
    if( shape.mode==0 )
    {
        float er = (y.x<0.0) ? shape.extrussionCorner1 : shape.extrussionCorner2;
        
        d = extrude( d, y, shape.extrussion-er, er );
    }

    // onion
    float onion = shape.onion;
    if( onion>0.00000001 ) d = dAbs(d + dSet(onion))-dSet(onion);

    // inflate
    d -= dSet(shape.inflate);
    
    return d;
}	



float SuperPrimitive3D( in vec3 p, in vec2 size, vec4 corners, float thickness, int mode, vec3 extrusion, float onion, float inflate)
{
    Shape shape;
    shape.width = size.x;
    shape.height = size.y;
    shape.corner0 = corners.x;
    shape.corner1 = corners.y;
    shape.corner2 = corners.z;
    shape.corner3 = corners.w;
    shape.thickness = thickness;
    shape.mode = mode;
    shape.extrussion = extrusion.x;
    shape.extrussionCorner1 = extrusion.y;
    shape.extrussionCorner2 = extrusion.z;
    shape.onion = onion;
    shape.inflate = inflate;
    return sdShape( dSetX(p.x), dSetY(p.y), dSetZ(p.z), shape ).x;
}
"""

TRANSITION_STATE_WRAPPER = """
const float[${N}] ${geometry_name}TS = float[${N}](${time_steps});
int ${geometry_name}StateIndex(float ts) {
    for (int i = 0; i < ${N} - 1; i++) {
        if (ts >= ${geometry_name}TS[i] && ts <= ${geometry_name}TS[i + 1]) {
            return i;
        }
    }
    return 0;
}

mat4 ${geometry_name}State(int index) {
    switch (index) {
        ${state_cases}
        // Add more states as needed
        default: return mat4(1.0); // Fallback
    }
}

vec2 ${geometry_name}Stateful(vec3 p, float ts) {

    int i = ${geometry_name}StateIndex(ts);
    // Get affine transformation matrices for states i and i+1
    mat4 state0 = ${geometry_name}State(i);      // mat4 for state i
    mat4 state1 = ${geometry_name}State(i + 1);  // mat4 for state i+1

    // Compute interpolation factor
    float alpha = (ts - ${geometry_name}TS[i]) / (${geometry_name}TS[i + 1] - ${geometry_name}TS[i]);

    // Interpolate between the two affine matrices
    mat4 interpolatedState = InterpAffine(state0, state1, alpha);
    // Transform the input position using the interpolated affine matrix
    vec3 transformedP = ApplyAffine(interpolatedState, p);
    // Here we should short circuit based on some constraint. 
    vec3 obj_translation = vec3(interpolatedState[3].xyz); // Last column
    mat3 obj_rotation = mat3(interpolatedState);           // Upper-left 3x3 for rotation

    // Define the axis-aligned bounding box in local space
    // Transform the point into the bounding box's local space
    vec3 localP = obj_rotation * (p + obj_translation);

    // Check if the point is inside the bounding box
    float temp_d = BoundingBox3D(localP, _${geometry_name}_bbox());
    if (temp_d > 0.2) return vec2(temp_d, 0.0);
    return ${geometry_name}SDF(transformedP);
}
"""

TRANSITION_STATE_WRAPPER_SINGLE = """
vec2 ${geometry_name}Stateful(vec3 p, float ts){
    mat4 state0 = ${geometry_name}_state0();      // mat4 for state i
    vec3 transformedP = ApplyAffine(state0, p);

    vec3 obj_translation = vec3(state0[3].xyz); // Last column
    mat3 obj_rotation = mat3(state0);           // Upper-left 3x3 for rotation

    // Define the axis-aligned bounding box in local space
    // Transform the point into the bounding box's local space
    vec3 localP = obj_rotation * (p + obj_translation);

    // Check if the point is inside the bounding box
    float temp_d = BoundingBox3D(localP, _${geometry_name}_bbox());
    if (temp_d > 0.2) return vec2(temp_d, 0.0);
    return ${geometry_name}SDF(transformedP);
}
"""

TRANSITION_FUNCTION_WRAPPER = """
mat4 ${function_name}(){
    mat4 pos_0 = mat4(1.0);
    ${code_lines}
    return res;
}
"""


TRANSITION_STATE_BETA_WRAPPER = """
const float[${N}] ${geometry_name}TS = float[${N}](${time_steps});
int ${geometry_name}StateIndex(float ts) {
    for (int i = 0; i < ${N} - 1; i++) {
        if (ts >= ${geometry_name}TS[i] && ts <= ${geometry_name}TS[i + 1]) {
            return i;
        }
    }
    return 0;
}

mat4 ${geometry_name}State(int index) {
    switch (index) {
        ${state_cases}
        // Add more states as needed
        default: return mat4(1.0); // Fallback
    }
}

vec2 ${geometry_name}Stateful(vec3 p, float ts) {

    int i = ${geometry_name}StateIndex(ts);
    // Get affine transformation matrices for states i and i+1
    mat4 state0 = ${geometry_name}State(i);      // mat4 for state i
    mat4 state1 = ${geometry_name}State(i + 1);  // mat4 for state i+1

    // Compute interpolation factor
    float alpha = (ts - ${geometry_name}TS[i]) / (${geometry_name}TS[i + 1] - ${geometry_name}TS[i]);

    // Interpolate between the two affine matrices
    mat4 interpolatedState = InterpAffine(state0, state1, alpha);
    // Transform the input position using the interpolated affine matrix
    vec3 transformedP = ApplyAffine(interpolatedState, p);
    // Here we should short circuit based on some constraint. 
    vec3 obj_translation = vec3(interpolatedState[3].xyz); // Last column
    mat3 obj_rotation = mat3(interpolatedState);           // Upper-left 3x3 for rotation

    // Define the axis-aligned bounding box in local space
    // Transform the point into the bounding box's local space
    vec3 localP = obj_rotation * (p + obj_translation);
    
    vec3 bbox_origin = _${geometry_name}_bbox_origin;
    localP = localP - bbox_origin;
    // Check if the point is inside the bounding box
    float temp_d = BoundingBox3D(localP, _${geometry_name}_bbox_scale);
    if (temp_d > 0.2) return vec2(temp_d, 0.0);
    return ${geometry_name}SDF(transformedP);
}
"""

TRANSITION_STATE_BETA_WRAPPER_SINGLE = """
vec2 ${geometry_name}Stateful(vec3 p, float ts){
    mat4 state0 = ${geometry_name}_state0();      // mat4 for state i
    vec3 transformedP = ApplyAffine(state0, p);

    vec3 obj_translation = vec3(state0[3].xyz); // Last column
    mat3 obj_rotation = mat3(state0);           // Upper-left 3x3 for rotation

    // Define the axis-aligned bounding box in local space
    // Transform the point into the bounding box's local space
    vec3 localP = obj_rotation * (p + obj_translation);
    vec3 bbox_origin = _${geometry_name}_bbox_origin;
    localP = localP - bbox_origin;
    // Check if the point is inside the bounding box
    float temp_d = BoundingBox3D(localP, _${geometry_name}_bbox_scale);
    if (temp_d > 0.1) return vec2(temp_d, 0.0);
    return ${geometry_name}SDF(transformedP);
}
"""


MAIN_WRAPPER_TEMPLATE = """
${uniform_initialization}
${function_definitions}

float SPACE_LIMIT=10.0;

vec2 OBJECT_SDF_AND_MATERIAL( in vec3 pos )
{
    vec2 res = vec2( pos.y, 0.0 );
    //if( Box3D( pos, vec3(SPACE_LIMIT, SPACE_LIMIT, SPACE_LIMIT) ) < res.x )
    float d = BoundingBox3D( pos, vec3(SPACE_LIMIT, SPACE_LIMIT, SPACE_LIMIT) ) ;
    if( d >= 0.1 ) return vec2( d, 0.0 );
    ${main_code}
    return res;
}
"""

SDF_FUNCTION_WRAPPER = """
vec2 ${function_name}(in vec3 pos_0){
    ${code_lines}
    return res;
}
"""

BOUNDING_BOX_BETA_WRAPPER = """
const vec3 _${geometry_name}_bbox_scale = ${bbox_scale};
const vec3 _${geometry_name}_bbox_origin = ${bbox_origin};
"""

BOUNDING_BOX_WRAPPER = """
vec3 _${geometry_name}_bbox(){
    ${code_lines}
    return ${bbox_param};
}
"""