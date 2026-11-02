//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat3 x3d_NormalMatrix;
uniform sampler2D u_teeth;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
in float a_tooth;
in float a_along;
out vec3 v_nrm;
out vec3 v_pos;
out vec4 v_col;
out vec3 v_obj;
flat out vec4 v_glow;
flat out vec2 v_lit;
out float v_along;
void main() {
  int row = int(a_tooth + 0.5);
  vec4 g = glowAt(u_teeth, row, u_time, 0.08, 0.35);
  v_glow = g;
  v_lit = litStrict(u_teeth, row, u_time);
  float age = max(g.z, 0.0);
  float amp = (0.25 + 0.75 * g.y) * 0.035 * exp(-age * 5.0) * step(0.003, g.x);
  vec4 pos = x3d_Vertex + vec4(0.0, amp * cos(age * 95.0) * a_along * a_along, 0.0, 0.0);
  vec4 p = x3d_ModelViewMatrix * pos;
  v_pos = p.xyz;
  v_nrm = x3d_NormalMatrix * x3d_Normal;
  v_col = x3d_Color;
  v_obj = x3d_Vertex.xyz;
  v_along = a_along;
  gl_Position = x3d_ProjectionMatrix * p;
}
