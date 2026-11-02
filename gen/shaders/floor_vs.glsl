//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform sampler2D u_tiles;
in vec4 x3d_Vertex;
in float a_tile;
in vec2 a_uv;
out vec3 v_world;
out vec2 v_uv;
flat out float v_tile;
flat out vec4 v_glow;
flat out vec2 v_lit;
void main() {
  int row = int(a_tile + 0.5);
  v_glow = glowAt(u_tiles, row, u_time, 0.08, 0.38);
  v_lit = litStrict(u_tiles, row, u_time);
  v_world = x3d_Vertex.xyz;
  v_uv = a_uv;
  v_tile = a_tile;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
