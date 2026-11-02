//@include common
//@include lantern_lib
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat3 x3d_NormalMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
in vec3 a_anchor;
in float a_phase;
in float a_glass;
out vec3 v_nrm;
out vec3 v_pos;
out vec4 v_col;
flat out float v_ph;
out float v_glass;
void main() {
  vec3 q = sway(x3d_Vertex.xyz, a_anchor, a_phase);
  vec4 p = x3d_ModelViewMatrix * vec4(q, 1.0);
  v_pos = p.xyz;
  v_nrm = x3d_NormalMatrix * x3d_Normal;
  v_col = x3d_Color;
  v_ph = a_phase;
  v_glass = a_glass;
  gl_Position = x3d_ProjectionMatrix * p;
}
