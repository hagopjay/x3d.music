//@include common
//@include motif_lib
// The probe draws the twelve motifs in reading order (A B C D / E F G H / I J K L, the top left first), each through the dome's own motif() lookup, so the test can compare what the
// lookup shows with the picture in the file.
in vec2 v_uv;
out vec4 x3d_FragColor;
void main() {
  vec2 g = v_uv * vec2(4.0, 3.0);
  float t = floor(g.x) + 4.0 * floor(g.y);
  vec4 c = motif(t, fract(g));
  x3d_FragColor = vec4(pow(c.rgb, vec3(1.0 / 2.2)), 1.0) * step(0.5, c.a);
}
