//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat3 x3d_NormalMatrix;
uniform sampler2D u_pins;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
in float a_pin;
out vec3 v_nrm;
out vec3 v_pos;
out vec4 v_col;
out vec3 v_obj;
flat out vec4 v_glow;
flat out vec2 v_lit;
void main() {
  int row = int(a_pin + 0.5);
  v_glow = glowAt(u_pins, row, u_time, 0.08, 0.35);
  v_lit = litStrict(u_pins, row, u_time);
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  v_pos = p.xyz;
  v_nrm = x3d_NormalMatrix * x3d_Normal;
  v_col = x3d_Color;
  v_obj = x3d_Vertex.xyz;
  gl_Position = x3d_ProjectionMatrix * p;
}
