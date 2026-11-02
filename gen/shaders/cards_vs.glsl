//@include common
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat4 x3d_CameraSpaceMatrix;
in vec4 x3d_Vertex;
in float a_kind;
in vec2 a_loc;
in float a_id;
in float a_t0;
in float a_t1;
in float a_fam;
out vec3 v_world;
out vec2 v_loc;
flat out float v_kind;
flat out vec4 v_ev;
flat out float v_fam;
void main() {
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  v_world = (x3d_CameraSpaceMatrix * p).xyz;
  v_loc = a_loc;
  v_kind = a_kind;
  v_ev = vec4(a_id, a_t0, a_t1, 0.0);
  v_fam = a_fam;
  gl_Position = x3d_ProjectionMatrix * p;
}
