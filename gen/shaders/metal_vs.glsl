//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat3 x3d_NormalMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
out vec3 v_nrm;
out vec3 v_pos;
out vec4 v_col;
out vec3 v_obj;
void main() {
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  v_pos = p.xyz;
  v_nrm = x3d_NormalMatrix * x3d_Normal;
  v_col = x3d_Color;
  v_obj = x3d_Vertex.xyz;
  gl_Position = x3d_ProjectionMatrix * p;
}
