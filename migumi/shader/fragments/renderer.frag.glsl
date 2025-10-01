// Need to be coupled with a
// OBJECT_SDF_AND_MATERIAL
// utils
const float SCENE_RADIUS = 100.0;
const vec3 BOX_CENTER    = vec3(0.0, 0.5, 0.0);
const vec3 BOX_HALF_SIZE = vec3(10.0, 5.0, 10.0);


vec2 raycast(in vec3 ro, in vec3 rd) {

    vec2 res = vec2(-1.0,-1.0);

    // 1) Sphere cull: cheap dot/mul vs. complex SDF
    float b = dot(ro, ro) - SCENE_RADIUS*SCENE_RADIUS;
    float c = dot(ro, rd);
    float disc = c*c - b;
    if (disc <= 0.0) return res;                // no intersection with sphere
    float s   = sqrt(disc);
    float t0  = -c - s;
    float t1  = -c + s;
    if (t1 < 0.0) return res;                   // both intersections behind camera

    float tmin = max(1.0, t0);
    float tmax = min(20.0, t1);

    // 2) Floor-plane (y=0) test
    float tp = -ro.y / rd.y;
    if (tp > 0.0 && tp < tmax) {
        tmax = tp;
        res = vec2(tp, 1.0);
    }

    // 3) AABB test
    vec3 inv_rd = 1.0 / rd;  // hoist reciprocal
    vec3 tA = ( BOX_CENTER - BOX_HALF_SIZE - ro ) * inv_rd;
    vec3 tB = ( BOX_CENTER + BOX_HALF_SIZE - ro ) * inv_rd;

    vec3 tMin3 = min(tA, tB);
    vec3 tMax3 = max(tA, tB);

    float tbmin = max( max(tMin3.x, tMin3.y), tMin3.z );
    float tbmax = min( min(tMax3.x, tMax3.y), tMax3.z );

    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        float t = tmin;
        for (int i = 0; i < 100 && t < tmax; i++) {
            vec2 h = OBJECT_SDF_AND_MATERIAL(ro + rd * t);
            if (abs(h.x) < 0.0001 * t) {
                res = vec2(t, h.y);
                break;
            }
            t += h.x;
        }
    }

    return res;
}

bool castShadows = false;

float calcSoftshadow( in vec3 ro, in vec3 rd, in float mint, in float tmax )
{
    // bounding volume
    if (!castShadows) return 1.0;
    float tp = (0.8-ro.y)/rd.y; 
    if( tp>0.0 ) tmax = min( tmax, tp );

    float res = 1.0;
    float t = mint;
    for( int i=0; i<64; i++ )
    {
		float h = OBJECT_SDF_AND_MATERIAL( ro + rd*t ).x;
        float s = clamp(8.0*h/t,0.0,1.0);
        res = min( res, s );
        t += clamp( h, 0.01, 0.2 );
        if( res<0.004 || t>tmax ) break;
    }
    res = clamp( res, 0.0, 1.0 );
    return res*res*(3.0-2.0*res);
}

// https://iquilezles.org/articles/normalsSDF
vec3 calcNormal( in vec3 pos )
{
    // inspired by tdhooper and klems - a way to prevent the compiler from inlining OBJECT_SDF_AND_MATERIAL() 4 times
    vec3 n = vec3(0.0);
    for( int i=0; i<4; i++ )
    {
        vec3 e = 0.5773*(2.0*vec3((((i+3)>>1)&1),((i>>1)&1),(i&1))-1.0);
        n += e*OBJECT_SDF_AND_MATERIAL(pos+0.0005*e).x;
      //if( n.x+n.y+n.z>100.0 ) break;
    }
    return normalize(n);
}



// https://iquilezles.org/articles/nvscene2008/rwwtt.pdf
float calcAO( in vec3 pos, in vec3 nor )
{
	float occ = 0.0;
    float sca = 1.0;
    for( int i=0; i<5; i++ )
    {
        float h = 0.01 + 0.12*float(i)/4.0;
        float d = OBJECT_SDF_AND_MATERIAL( pos + h*nor ).x;
        occ += (h-d)*sca;
        sca *= 0.95;
        if( occ>0.35 ) break;
    }
    return clamp( 1.0 - 3.0*occ, 0.0, 1.0 ) * (0.5+0.5*nor.y);
}

// https://iquilezles.org/articles/checkerfiltering
float checkersGradBox( in vec2 p, in vec2 dpdx, in vec2 dpdy )
{
    // filter kernel
    vec2 w = abs(dpdx)+abs(dpdy) + 0.001;
    // analytical integral (box filter)
    vec2 i = 2.0*(abs(fract((p-0.5*w)*0.5)-0.5)-abs(fract((p+0.5*w)*0.5)-0.5))/w;
    // xor pattern
    return 0.5 - 0.5*i.x*i.y;                  
}


// vec3 render( in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy )
// { 
//     // ray -> color

//     // background
//     vec3 col = vec3(0.7, 0.7, 0.9) - max(rd.y,0.0)*0.3;
    
//     // raycast scene
//     vec2 res = raycast(ro,rd);
//     float t = res.x;
// 	float m = res.y;

//     // Material logic
//     if( m>-0.5 )
//     {
//         vec3 pos = ro + t*rd;
//         vec3 nor = (m<1.5) ? vec3(0.0,1.0,0.0) : calcNormal( pos );
//         vec3 ref = reflect( rd, nor );
        
//         // material        
//         col = 0.2 + 0.2*sin( m*2.0 + vec3(0.0,1.0,2.0) );
//         float ks = 1.0;
        
//         if( m<1.5 )
//         {
//             // project pixel footprint into the plane
//             vec3 dpdx = ro.y*(rd/rd.y-rdx/rdx.y);
//             vec3 dpdy = ro.y*(rd/rd.y-rdy/rdy.y);

//             float f = checkersGradBox( 3.0*pos.xz, 3.0*dpdx.xz, 3.0*dpdy.xz );
//             col = 0.15 + f*vec3(0.05);
//             ks = 0.4;
//         }

//         // lighting
//         float occ = calcAO( pos, nor );
        
// 		vec3 lin = vec3(0.0);

//         // sun
//         {
//             vec3  lig = normalize( vec3(-0.5, 0.4, -0.6) );
//             vec3  hal = normalize( lig-rd );
//             float dif = clamp( dot( nor, lig ), 0.0, 1.0 );
//           //if( dif>0.0001 )
//         	      dif *= calcSoftshadow( pos, lig, 0.02, 2.5 );
//         	    //   dif *= calcSoftshadow( pos, lig, 0.01, 3.0, 0.1 );
// 			float spe = pow( clamp( dot( nor, hal ), 0.0, 1.0 ),16.0);
//                   spe *= dif;
//                   spe *= 0.04+0.96*pow(clamp(1.0-dot(hal,lig),0.0,1.0),5.0);
//                 //spe *= 0.04+0.96*pow(clamp(1.0-sqrt(0.5*(1.0-dot(rd,lig))),0.0,1.0),5.0);
//             lin += col*2.20*dif*vec3(1.30,1.00,0.70);
//             lin +=     5.00*spe*vec3(1.30,1.00,0.70)*ks;
//         }
//         // sky
//         {
//             float dif = sqrt(clamp( 0.5+0.5*nor.y, 0.0, 1.0 ));
//                   dif *= occ;
//             float spe = smoothstep( -0.2, 0.2, ref.y );
//                   spe *= dif;
//                   spe *= 0.04+0.96*pow(clamp(1.0+dot(nor,rd),0.0,1.0), 5.0 );
//           //if( spe>0.001 )
//                   spe *= calcSoftshadow( pos, ref, 0.02, 2.5 );
//         	    //   spe *= calcSoftshadow( pos, ref, 0.01, 3.0, 0.1 );
//             lin += col*0.60*dif*vec3(0.40,0.60,1.15);
//             lin +=     2.00*spe*vec3(0.40,0.60,1.30)*ks;
//         }
//         // back
//         {
//         	float dif = clamp( dot( nor, normalize(vec3(0.5,0.0,0.6))), 0.0, 1.0 )*clamp( 1.0-pos.y,0.0,1.0);
//                   dif *= occ;
//         	lin += col*0.55*dif*vec3(0.25,0.25,0.25);
//         }
//         // sss
//         {
//             float dif = pow(clamp(1.0+dot(nor,rd),0.0,1.0),2.0);
//                   dif *= occ;
//         	lin += col*0.25*dif*vec3(1.00,1.00,1.00);
//         }
        
// 		col = lin;

//         col = mix( col, vec3(0.7,0.7,0.9), 1.0-exp( -0.0001*t*t*t ) );
//     }

// 	return vec3( clamp(col,0.0,1.0) );
// }

struct Material {
    vec3 albedo;
    float ks;
};

// Choose material properties based on hit id
Material getMaterial(float m, vec3 pos, vec3 ro, vec3 rd, vec3 rdx, vec3 rdy) {
    Material mat;
    if (m < 1.5) {
        // Floor checker
        vec3 dpdx = ro.y * (rd / rd.y - rdx / rdx.y);
        vec3 dpdy = ro.y * (rd / rd.y - rdy / rdy.y);
        float f = checkersGradBox(3.0 * pos.xz, 3.0 * dpdx.xz, 3.0 * dpdy.xz);
        mat.albedo = vec3(0.15) + f * vec3(0.05);
        mat.ks     = 0.4;
    } else {
        // Object color
        mat.albedo = 0.2 + 0.2 * sin(m * 2.0 + vec3(0.0, 1.0, 2.0));
        mat.ks     = 1.0;
    }
    return mat;
}

// Compute lighting for a hit
vec3 calcLighting(vec3 pos, vec3 nor, vec3 ref, vec3 rd, Material mat, vec3 lig) {
    float occ = calcAO(pos, nor);
    vec3 lin = vec3(0.0);

    // Sun light
    // vec3 lig = normalize(vec3(-0.5, 0.4, -0.6));
    vec3 hal = normalize(lig - rd);
    float dif = clamp(dot(nor, lig), 0.0, 1.0);
    dif *= calcSoftshadow(pos, lig, 0.02, 2.5);
    float spe = pow(clamp(dot(nor, hal), 0.0, 1.0), 16.0);
    spe *= dif * (0.04 + 0.96 * pow(clamp(1.0 - dot(hal, lig), 0.0, 1.0), 5.0));
    lin += mat.albedo * 2.2 * dif * vec3(1.3, 1.0, 0.7);
    lin += 5.0 * spe * vec3(1.3, 1.0, 0.7) * mat.ks;

    // Sky light
    dif = sqrt(clamp(0.5 + 0.5 * nor.y, 0.0, 1.0));
    dif *= occ;
    spe = smoothstep(-0.2, 0.2, ref.y);
    spe *= dif * (0.04 + 0.96 * pow(clamp(1.0 + dot(nor, rd), 0.0, 1.0), 5.0));
    spe *= calcSoftshadow(pos, ref, 0.02, 2.5);
    lin += mat.albedo * 0.6 * dif * vec3(0.4, 0.6, 1.15);
    lin += 2.0 * spe * vec3(0.4, 0.6, 1.30) * mat.ks;

    // Back light
    dif = clamp(dot(nor, normalize(vec3(0.5, 0.0, 0.6))), 0.0, 1.0) * clamp(1.0 - pos.y, 0.0, 1.0);
    dif *= occ;
    lin += mat.albedo * 0.55 * dif * vec3(0.25);

    // Subsurface
    dif = pow(clamp(1.0 + dot(nor, rd), 0.0, 1.0), 2.0);
    dif *= occ;
    lin += mat.albedo * 0.25 * dif;

    return lin;
}

// Cleaned-up render function
vec3 render(in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy, vec3 lig) {
    // Background
    vec3 bg = vec3(0.7, 0.7, 0.9) - max(rd.y, 0.0) * 0.3;

    // Raycast
    vec2 hit = raycast(ro, rd);
    if (hit.x < 0.0) return bg;

    float t  = hit.x;
    float m  = hit.y;
    vec3  pos = ro + rd * t;
    vec3  nor = (m < 1.5) ? vec3(0.0, 1.0, 0.0) : calcNormal(pos);
    vec3  ref = reflect(rd, nor);

    // Material determination
    Material mat = getMaterial(m, pos, ro, rd, rdx, rdy);

    // Lighting
    vec3 color = calcLighting(pos, nor, ref, rd, mat, lig);

    // Fog
    float fogFactor = 1.0 - exp(-0.0001 * t * t * t);
    return mix(color, bg, fogFactor);
}
