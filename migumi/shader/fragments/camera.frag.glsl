
// uniform vec3 origin;
uniform vec2 resolution;
uniform float cameraAngleX;
uniform float cameraAngleY;
uniform float cameraDistance;
uniform vec3 cameraOrigin;
uniform float sunAzimuth;    // 0…2π, rotation around the Y-axis
uniform float sunElevation;  // –π/2…+π/2, angle above the horizon
// vec3 origin = vec3(0.0, 0.5, 0.0);
// float cameraAngleX = 0.25;
// float cameraAngleY = 0.5;
// float cameraDistance = 4.0;
int ZERO = 0;


// focal length
const float fl = 2.5;
#define AA 1   // make this 2 or 3 for antialiasing


mat3 setCamera( in vec3 ro, in vec3 ta, float cr )
{
	vec3 cw = normalize(ta-ro);
	vec3 cp = vec3(sin(cr), cos(cr),0.0);
	vec3 cu = normalize( cross(cw,cp) );
	vec3 cv =          ( cross(cu,cw) );
    return mat3( cu, cv, cw );
}

vec3 getSunDirection() {
    // Y-up convention: elevation = 0 → horizon, +π/2 → straight up
    float x =  cos(sunElevation) * sin(sunAzimuth);
    float y =  sin(sunElevation);
    float z =  cos(sunElevation) * cos(sunAzimuth);
    return normalize(vec3(x, y, z));
}


void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 mo = vec2(0.0, 0.0);
    // camera	
    vec3 ta = vec3( 0.0, 1.0, -0.0 ) + cameraOrigin;
    vec3 ro = ta + cameraDistance * vec3(
        cos(cameraAngleX) * sin(cameraAngleY), // X component
        sin(cameraAngleX),                     // Y component (elevation)
        cos(cameraAngleX) * cos(cameraAngleY)  // Z component
    );
    // camera-to-world transformation
    mat3 ca = setCamera( ro, ta, 0.0 );
    vec3 tot = vec3(0.0);
    vec3 lig = getSunDirection();
    for( int m=ZERO; m<AA; m++ )
    for( int n=ZERO; n<AA; n++ )
    {
        // pixel coordinates
        vec2 o = vec2(float(m),float(n)) / float(AA) - 0.5;


        vec2 p = (2.0*(fragCoord+o)-resolution.xy)/resolution.xy;

        vec3 rd = ca * normalize( vec3(p,fl) );


        vec2 px = (2.0 * (fragCoord + vec2(1.0, 0.0)) - resolution.xy) / resolution.xy;
        vec2 py = (2.0 * (fragCoord + vec2(0.0, 1.0)) - resolution.xy) / resolution.xy;

        vec3 rdx = ca * normalize(vec3(px, fl));
        vec3 rdy = ca * normalize(vec3(py, fl));

        // render	
        vec3 col = render( ro, rd, rdx, rdy , lig);

        // gain
        // col = col*3.0/(2.5+col);
        
		// gamma
        col = pow( col, vec3(0.4545) );

        tot += col;
    }
    tot /= float(AA*AA);
    
    fragColor = vec4( tot, 1.0 );
}