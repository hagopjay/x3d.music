//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat4 x3d_CameraSpaceMatrix;
uniform mat3 x3d_NormalMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_Color;
in float a_mat;
out vec3 v_world;
out vec3 v_nrm;
out vec3 v_col;
flat out float v_mat;
void main() {
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  v_world = (x3d_CameraSpaceMatrix * p).xyz;
  v_nrm = mat3(x3d_CameraSpaceMatrix) * (x3d_NormalMatrix * x3d_Normal);
  v_col = x3d_Color.rgb * 2.0;
  v_mat = a_mat;
  gl_Position = x3d_ProjectionMatrix * p;
}
