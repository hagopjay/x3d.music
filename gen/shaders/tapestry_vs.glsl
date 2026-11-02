//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in vec2 a_uv;
out vec2 v_uv;
out vec3 v_obj;
void main() {
  v_uv = a_uv;
  v_obj = x3d_Vertex.xyz;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
