//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat4 x3d_CameraSpaceMatrix;
in vec4 x3d_Vertex;
in vec2 a_uv;
out vec2 v_uv;
out vec3 v_world;
void main() {
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  v_world = (x3d_CameraSpaceMatrix * p).xyz;
  v_uv = a_uv;
  gl_Position = x3d_ProjectionMatrix * p;
}
