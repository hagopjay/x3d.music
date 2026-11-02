//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform sampler2D u_pins;
uniform float u_haloSize;
in vec4 x3d_Vertex;
in vec2 a_corner;
in float a_pin;
out vec2 v_c;
flat out vec4 v_glow;
void main() {
  int row = int(a_pin + 0.5);
  vec4 g = glowAt(u_pins, row, u_time, 0.08, 0.35);
  v_glow = g;
  float size = u_haloSize * (0.35 + 0.65 * g.x) * step(0.004, g.x);
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  p.xy += a_corner * size;
  v_c = a_corner;
  gl_Position = x3d_ProjectionMatrix * p;
}
