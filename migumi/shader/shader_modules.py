from sysl.shader.shader_module import register_shader_module, SMMap
from sysl.shader.shader_mod_ext import CustomFunctionShaderModule
from string import Template

BaseHelpers = register_shader_module("""
@name BaseHelpers
@dependencies
@inputs
@outputs
float dot2( in vec2 v ) { return dot(v,v); }
float dot2( in vec3 v ) { return dot(v,v); }
float ndot( in vec2 a, in vec2 b ) { return a.x*b.x - a.y*b.y; }
float cro(vec2 v1, vec2 v2) {
    return v1.x * v2.y - v1.y * v2.x;
}
""")
ApplyHeight = register_shader_module("""
@name ApplyHeight
@inputs pos, sdf2d, height
@outputs dist
@dependencies
float ApplyHeight( vec3 p, float sdf2d, float height )
{   

    vec2 d = vec2(sdf2d, max(p.z - height, -p.z));
    return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}
vec2 ApplyHeight( vec3 p, vec2 sdf2d, float height )
{   

    vec2 d = vec2(sdf2d.x, max(p.z - height, -p.z));
    float sdf = min(max(d.x,d.y),0.0) + length(max(d,0.0));
    return vec2(sdf, sdf2d.y);
}
""")

LocalHFCoord = register_shader_module("""
@name LocalHFCoord
@inputs p, plane_origin, plane_normal
@outputs local_p
@dependencies
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
""")


PolyArc2DHelper = register_shader_module("""
@name PolyArc2DHelper
@inputs p, a, b
@outputs d, s
@dependencies BaseHelpers

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
""")


PolyArc2DInner = Template("""
float ${function_name}( in vec2 p, in vec3[${n_points}] v )
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
""")

class PolyArc2D(CustomFunctionShaderModule):
    def __init__(self, name=None,template=None, *args, **kwargs):
        if template is None:
            template = PolyArc2DInner
        if name is None:
            name = "PolyArc2D"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["PolyArc2DHelper",]
        self.n_points = []
        self.func_names = []
    def register_hit(self, *args, **kwargs):
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        num_points = kwargs.get("num_points", None)
        assert num_points is not None, "Number of points is required"
        self.n_points.append(num_points)
        self.func_names.append(function_name)
        self.function_names.add(function_name)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for function_name in self.function_names:
            ind = self.func_names.index(function_name)
            code = self.template.substitute(function_name=function_name, n_points=self.n_points[ind])
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


SMMap["PolyArc2D"] = PolyArc2D
