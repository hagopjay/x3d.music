uniform sampler2D u_motifs;
// The dome's twelve motifs (art/dome-motifs.jpg: 4 x 3 tiles, each picture 480 px inside a 16 px mirrored gutter), looked up mirrored so a cell's edges continue into its neighbours.
// Tile t is the motif letter A..L, row by row from the top left; X_ITE 16.5.1 puts the picture's top row at t = 0 (witnesses/atlas_test.mjs holds that). Colours are sRGB bytes in the file and linear here.
vec4 motif(float t, vec2 f) {
  vec2 m = 1.0 - abs(1.0 - mod(f, 2.0));
  vec2 at = vec2(mod(t, 4.0), floor(t / 4.0));
  vec4 c = texture(u_motifs, (at + 0.03125 + m * 0.9375) / vec2(4.0, 3.0));
  return vec4(pow(c.rgb, vec3(2.2)), c.a);
}
