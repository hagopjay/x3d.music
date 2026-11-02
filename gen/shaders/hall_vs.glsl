//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
in float a_mat;
out vec3 v_world;
out vec3 v_nrm;
out vec3 v_col;
flat out float v_mat;
void main() {
  v_world = x3d_Vertex.xyz;
  v_nrm = x3d_Normal;
  v_col = x3d_Color.rgb * 2.0;
  v_mat = a_mat;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
