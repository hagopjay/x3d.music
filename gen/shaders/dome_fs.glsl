//@include common
//@include tile_lib
//@include motif_lib
uniform float u_key;
uniform float u_sec;
uniform float u_open;
uniform float u_qpm;
in vec3 v_dir;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 d = normalize(v_dir);
  float el = acos(clamp(d.y, -1.0, 1.0));
  float az = atan(d.z, d.x);
  float q = u_time * u_qpm / 60.0;
  float turn = (floor(q) + smoothstep(0.0, 0.35, fract(q))) / 12.0 * TAU;
  float seg = TAU / 12.0;
  float a = abs(mod(az + turn, seg) - 0.5 * seg);
  vec2 p = vec2(cos(a), sin(a)) * el;
  vec2 g = p * (2.6 + 0.3 * mod(u_sec, 4.0));
  vec2 cell = floor(g);
  vec3 c1, c2, c3, c4;
  palette(u_key, c1, c2, c3, c4);
  float seed = hash21(cell + u_sec * 7.0);
  vec3 col = tileArt(fract(g), seed * 6.0, 8.0 + 2.0 * floor(seed * 3.0), c1, c2, c3, c4);
  // The painted motifs, when the picture has loaded (alpha is 0 until then, and for good if it never does: the procedural tile above stays). A section has its motif, A to I, the two endings keep
  // the refrain's (I) and the coda has J; the first bars open under the hush (K) and the final chord opens the dome into the gold (L). Each cell's glaze is a little different.
  float sec = floor(u_sec + 0.5);
  float tSec = sec <= 8.5 ? sec : (sec < 10.5 ? 8.0 : 9.0);
  vec4 pic = motif(tSec, g);
  if (pic.a > 0.5) {
    col = pic.rgb;
    float hush = (1.0 - smoothstep(3.0, 7.6, u_time)) * step(sec, 0.5);
    if (hush > 0.002) col = mix(col, motif(10.0, g).rgb, hush);
    float fin = smoothstep(0.0, 0.7, u_open);
    if (fin > 0.002) col = mix(col, motif(11.0, g).rgb, fin);
    col *= 0.90 + 0.20 * seed;
  }
  float warm = smoothstep(0.55, 1.5, el);
  float pulse = 1.0 + 0.18 * exp(-fract(q) * 5.0) * (1.0 - 0.8 * u_calm);
  col *= (vec3(1.0, 0.74, 0.5) * warm * 0.75 + vec3(0.30, 0.42, 0.95) * 0.22) * pulse;
  col *= 1.0 - 0.7 * smoothstep(1.40, 1.57, el);
  float rad = u_open * 0.62;
  float star = step(0.992, hash21(floor(d.xz / max(d.y, 0.2) * 70.0)));
  vec3 sky = mix(S(6.0, 12.0, 40.0), S(14.0, 28.0, 70.0), el) + star * vec3(1.0, 0.95, 0.85) * 1.2;
  float hole = smoothstep(rad, rad - 0.04, el) * step(0.001, u_open);
  col = mix(col, sky, hole);
  x3d_FragColor = vec4(finish(col), 1.0);
}
