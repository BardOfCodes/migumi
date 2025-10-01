float dot2( in vec2 v ) { return dot(v,v); }
float dot2( in vec3 v ) { return dot(v,v); }
float ndot( in vec2 a, in vec2 b ) { return a.x*b.x - a.y*b.y; }
float cro(vec2 v1, vec2 v2) {
    return v1.x * v2.y - v1.y * v2.x;
}