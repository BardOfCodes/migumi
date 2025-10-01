
uniform vec2 uniform_0;

vec2 MinRes( vec2 a, vec2 b )
{
    return (a.x<b.x) ? a : b;
}


float Union( float d1, float d2 )
{
        return (d1<d2) ? d1 : d2;
}


float ApplyHeight( vec3 p, float sdf2d, float height )
{   

    vec2 d = vec2(sdf2d, max(p.z - height, -p.z));
    return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}


vec2 SetMaterial( float sdf2d, float material_id )
{   
    vec2 res = vec2( sdf2d, material_id );
    return res;
}


float Difference( float d1, float d2 )
{
    return (d1>-d2) ? d1 : -d2;
}


float Intersection( float d1, float d2 )
{
        return (d1 > d2) ? d1 : d2;
}


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


float Box3D( vec3 p, vec3 b )
{
    vec3 d = abs(p) - b;
    return min(max(d.x,max(d.y,d.z)),0.0) + length(max(d,0.0));
}


float Rectangle2D( in vec2 p, in vec2 b )
{
    vec2 d = abs(p)-b;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}


vec3 LocalHFCoord(vec3 p, vec3 plane_origin, vec3 plane_normal){

    plane_normal = plane_normal / length(plane_normal);
    p = p - plane_origin;
    // projection
    vec3 normal_proj = dot(p, plane_normal) * plane_normal;
    vec3 z_axis = vec3(0.0, 0.0, 1.0);
    vec3 x_axis = cross(z_axis, plane_normal);
    x_axis.x += 1e-6;
    x_axis = x_axis / length(x_axis);
    vec3 y_axis = cross(plane_normal, x_axis);
    y_axis = y_axis / length(y_axis);

    vec3 local_p = vec3(dot(p, x_axis), dot(p, y_axis), dot(p, plane_normal));
    return local_p;
} 


vec2 sdf_call_0(in vec3 pos_0){
    vec3 pos_1 = LocalHFCoord(pos_0, vec3(0, 0, 0), vec3(0, 1, 0));
vec2 pos_1_xy = pos_1.xy;
float sdf_0 = Rectangle2D(pos_1_xy, vec2(0.500000000000000, 0.500000000000000));
float sdf_1 = ApplyHeight(pos_1, sdf_0, 1.0);
vec3 pos_2 = LocalHFCoord(pos_0, vec3(0, 1, 0), vec3(1, 0, 1));
vec2 pos_2_xy = pos_2.xy;
float sdf_2 = Rectangle2D(pos_2_xy, vec2(0.500000000000000, 0.250000000000000));
float sdf_3 = ApplyHeight(pos_2, sdf_2, 0.750000000000000);
float sdf_4 = Difference(sdf_1, sdf_3);
vec2 res = SetMaterial(sdf_4, 3.0);
    return res;
}


vec2 sdf_call_1(in vec3 pos_0){
    vec3 pos_1 = LocalHFCoord(pos_0, vec3(1, 1.50000000000000, 1), vec3(0, -1, 0));
vec2 pos_1_xy = pos_1.xy;
float sdf_0 = Rectangle2D(pos_1_xy, vec2(0.500000000000000, 0.500000000000000));
float sdf_1 = ApplyHeight(pos_1, sdf_0, 0.500000000000000);
vec3 pos_2 = LocalHFCoord(pos_0, vec3(1, 1.50000000000000, 1), vec3(0, -1, 0));
vec2 pos_2_xy = pos_2.xy;
float sdf_2 = Rectangle2D(pos_2_xy, vec2(0.500000000000000, 0.500000000000000));
float sdf_3 = ApplyHeight(pos_2, sdf_2, 1.0);
vec3 pos_3 = LocalHFCoord(pos_0, vec3(1, 0.750000000000000, 1), vec3(1, 0, 1));
vec2 pos_3_xy = pos_3.xy;
float sdf_4 = Rectangle2D(pos_3_xy, uniform_0);
float sdf_5 = ApplyHeight(pos_3, sdf_4, 0.750000000000000);
float sdf_6 = Intersection(sdf_3, sdf_5);
float sdf_7 = Union(sdf_1, sdf_6);
vec2 res = SetMaterial(sdf_7, 2.0);
    return res;
}


float SPACE_LIMIT=3.0;

vec2 OBJECT_SDF_AND_MATERIAL( in vec3 pos )
{
    vec2 res = vec2( pos.y, 0.0 );
    if( Box3D( pos, vec3(SPACE_LIMIT, SPACE_LIMIT, SPACE_LIMIT) ) < res.x )
    {   
        vec2 res_0 = sdf_call_0(pos);
vec2 res_1 = sdf_call_1(pos);
res = MinRes(res_0, res_1);
        
    }
    return res;
}