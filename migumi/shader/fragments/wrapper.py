
template = """#version 300 es

#ifdef GL_ES
precision mediump float;
#endif

out vec4 FragColor;  // Define the output color variable

${INNER_CODE}


void main(void)
{
  mainImage(FragColor, gl_FragCoord.xy);
}
"""

