//@include common
//@include lantern_lib
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in vec4 x3d_Color;
in vec2 a_corner;
in float a_size;
in float a_phase;
in vec3 a_anchor;
out vec2 v_c;
out vec3 v_rgb;
void main() {
  float fl = 0.9 + 0.1 * sin(u_time * 7.0 + a_phase * 6.28) + 0.05 * sin(u_time * 13.3 + a_phase * 17.0);
  vec3 q = sway(x3d_Vertex.xyz, a_anchor, a_phase);
  vec4 p = x3d_ModelViewMatrix * vec4(q, 1.0);
  p.xy += a_corner * a_size * fl;
  v_c = a_corner;
  v_rgb = x3d_Color.rgb * 2.0;
  gl_Position = x3d_ProjectionMatrix * p;
}
