//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec2 v_uv;
void main() {
  v_uv = vec2((x3d_Vertex.x + 2.0) / 4.0, (1.5 - x3d_Vertex.y) / 3.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
