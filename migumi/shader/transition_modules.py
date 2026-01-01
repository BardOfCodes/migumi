from sysl.shader.shader_module import register_shader_module, SMMap
from string import Template
from sysl.shader.shader_mod_ext import CustomFunctionShaderModule

Slerp = register_shader_module("""
@name slerp
@inputs q0, q1, alpha
@outputs res
@dependencies
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
""")


TranslationMatrix = register_shader_module("""
@name TranslationMatrix
@inputs translation
@outputs res
@dependencies
mat4 TranslationMatrix(vec3 translation) {
    mat4 result = mat4(1.0); // Identity matrix
    result[3] = vec4(translation, 1.0); // Set the translation column
    return result;
}
""")
QuatRotationMatrix = register_shader_module("""
@name QuatRotationMatrix
@inputs quaternion
@outputs res
@dependencies
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
""")
EulerRotationMatrix = register_shader_module("""
@name EulerRotationMatrix
@inputs rotation
@outputs res
@dependencies
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
""")
RotationFromMatrix = register_shader_module("""
@name RotationFromMatrix
@inputs mat
@outputs res
@dependencies
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
""")
InterpAffine = register_shader_module("""
@name InterpAffine
@inputs matA, matB, alpha
@outputs res
@dependencies slerp, RotationFromMatrix, QuatRotationMatrix
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
""")

ApplyAffine = register_shader_module("""
@name ApplyAffine
@inputs affineMatrix, position
@outputs res
@dependencies
vec3 ApplyAffine(mat4 affineMatrix, vec3 position) {
    // Convert vec3 to vec4 with homogeneous coordinates
    vec4 pos4D = vec4(position, 1.0);

    // Apply the affine transformation
    vec4 transformedPos = affineMatrix * pos4D;

    // Return the resulting vec3
    return transformedPos.xyz;
}
""")


TRANSITION_FUNCTION_WRAPPER = Template("""
mat4 ${function_name}(){
    mat4 pos_0 = mat4(1.0);
    ${code_lines}
    return res;
}
""")



TRANSITION_STATE_BETA_WRAPPER = Template("""
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

${out_type} ${geometry_name}Stateful(vec3 p, float ts) {

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
    return ${geometry_name}SDF(transformedP);
}
""")    


class TransitionWrapper(CustomFunctionShaderModule):

    def __init__(self, name=None,template=None, *args, **kwargs):
        if template is None:
            template = TRANSITION_STATE_BETA_WRAPPER
        if name is None:
            name = "TransitionWrapper"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["InterpAffine", "ApplyAffine",]
        self.geometry_names = []
        self.state_cases = []
        self.time_steps = []
        self.N = []
        self.time_steps = []
        self.func_names = []
        self.out_types = []
    def register_hit(self, *args, **kwargs):
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        self.function_names.add(function_name)
        self.func_names.append(function_name)

        out_type = kwargs.get("out_type", None)
        assert out_type is not None, "Out type is required"
        self.out_types.append(out_type)
        geometry_name = kwargs.get("geometry_name", None)
        assert geometry_name is not None, "Geometry name is required"
        self.geometry_names.append(geometry_name)

        state_cases = kwargs.get("state_cases", None)
        assert state_cases is not None, "State cases are required"
        self.state_cases.append(state_cases)

        time_steps = kwargs.get("time_steps", None)
        assert time_steps is not None, "Time steps are required"
        self.time_steps.append(time_steps)

        N = kwargs.get("N", None)
        assert N is not None, "N is required"
        self.N.append(N)

        deps = kwargs.get("deps", None)
        assert deps is not None, "Dependencies are required"
        self.dependencies.extend(deps)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for function_name in self.function_names:
            ind = self.func_names.index(function_name)
            code = self.template.substitute(func_name=function_name, 
            geometry_name=self.geometry_names[ind],
            state_cases=self.state_cases[ind],
                N=self.N[ind],
                time_steps=self.time_steps[ind],
                out_type=self.out_types[ind],
            )
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


TRANSITION_STATE_BETA_WRAPPER_SINGLE = Template("""
${out_type} ${function_name}(vec3 p, float ts){
    mat4 state0 = ${geometry_name}_state0();      // mat4 for state i
    vec3 transformedP = ApplyAffine(state0, p);

    vec3 obj_translation = vec3(state0[3].xyz); // Last column
    mat3 obj_rotation = mat3(state0);           // Upper-left 3x3 for rotation

    // Define the axis-aligned bounding box in local space
    // Transform the point into the bounding box's local space
    vec3 localP = obj_rotation * (p + obj_translation);
    // Check if the point is inside the bounding box
    return ${geometry_name}SDF(transformedP);
}
""")

class TransitionWrapperSingle(CustomFunctionShaderModule):

    def __init__(self, name=None,template=None, *args, **kwargs):
        if template is None:
            template = TRANSITION_STATE_BETA_WRAPPER_SINGLE
        if name is None:
            name = "TransitionWrapperSingle"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["InterpAffine", "ApplyAffine",]
        self.geometry_names = []
        self.func_names = []
        self.out_types = []
    def register_hit(self, *args, **kwargs):
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        self.function_names.add(function_name)
        self.func_names.append(function_name)

        geometry_name = kwargs.get("geometry_name", None)
        assert geometry_name is not None, "Geometry name is required"
        self.geometry_names.append(geometry_name)

        deps = kwargs.get("deps", None)
        assert deps is not None, "Dependencies are required"
        self.dependencies.extend(deps)
        out_type = kwargs.get("out_type", None)
        assert out_type is not None, "Out type is required"
        self.out_types.append(out_type)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for function_name in self.function_names:
            ind = self.func_names.index(function_name)
            code = self.template.substitute(function_name=function_name,
            geometry_name=self.geometry_names[ind],
            out_type=self.out_types[ind],
            )
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code

SMMap["TransitionWrapper"] = TransitionWrapper
SMMap["TransitionWrapperSingle"] = TransitionWrapperSingle