//@include common
//@include ode_lib
// The rose window is the circle of fifths: twelve sectors, C at the top, a fifth clockwise each. The sectors of the pitch classes in the current chord flare (u_chords: one row a sector,
// events are the chord spans); the hub takes the colour of the key and swells with the harmonic tension.
uniform sampler2D u_chords;
in vec2 v_uv;
out vec4 x3d_FragColor;
vec3 glass(int s) {
  int m = s - 5 * (s / 5);
  return m == 0 ? S(30.0, 74.0, 190.0) : (m == 1 ? S(190.0, 36.0, 56.0) : (m == 2 ? S(24.0, 150.0, 112.0) : (m == 3 ? S(232.0, 172.0, 52.0) : S(130.0, 56.0, 170.0))));
}
float cuts(float d, float w) { return smoothstep(w, w * 0.45, d); }
void main() {
  vec2 p = v_uv;
  float r = length(p);
  float ang = atan(p.x, p.y);
  float sec = mod(floor(ang / (TAU / 12.0) + 0.5) + 12.0, 12.0);
  int s = int(sec + 0.5);
  float within = fract(ang / (TAU / 12.0) + 0.5) - 0.5;
  vec4 gl = glowAt(u_chords, s, u_time, 0.12, 0.8);
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec2 axis = vec2(sin(sec * TAU / 12.0), cos(sec * TAU / 12.0));
  // lead lines: four rings, a mullion between sectors, a petal in every sector inside, a small round window between each pair outside
  float lead = 0.0;
  lead = max(lead, cuts(abs(r - 0.17), 0.030));
  lead = max(lead, cuts(abs(r - 0.48), 0.030));
  lead = max(lead, cuts(abs(r - 0.78), 0.030));
  lead = max(lead, cuts(abs(r - 0.935), 0.045));
  float arc = (0.5 - abs(within)) * r * (TAU / 12.0);
  lead = max(lead, cuts(arc, 0.030) * step(0.17, r) * step(r, 0.935));
  float pd = length(p - axis * 0.325);
  lead = max(lead, cuts(abs(pd - 0.125), 0.024) * step(0.17, r) * step(r, 0.48));
  float a24 = floor(ang / (TAU / 24.0)) * (TAU / 24.0) + TAU / 48.0;
  vec2 c24 = vec2(sin(a24), cos(a24)) * 0.855;
  float cd = length(p - c24);
  lead = max(lead, cuts(abs(cd - 0.055), 0.020) * step(0.78, r) * step(r, 0.935));
  vec3 base = glass(int(mod(sec * 7.0, 12.0)));
  vec3 petal = glass(int(mod(sec * 7.0 + 2.0, 12.0)));
  vec3 gl2 = r < 0.48 ? mix(base, petal, smoothstep(0.125, 0.10, pd)) : (r > 0.78 ? mix(base, glass(int(mod(sec * 7.0 + 4.0, 12.0))), smoothstep(0.055, 0.04, cd)) : base);
  float n = 0.55 + 0.9 * fbm(p * 9.0 + sec);
  float back = 0.55 + 0.7 * smoothstep(1.0, 0.0, r);
  vec3 col = gl2 * n * back * 1.25;
  col = mix(col, vec3(0.012, 0.012, 0.02), lead);
  float g = gl.x * (1.0 - 0.8 * u_calm);
  col += gl2 * g * 3.4 * (1.0 - lead) + S(255.0, 240.0, 210.0) * g * g * 0.9 * (1.0 - lead);
  float hub = smoothstep(0.17, 0.15, r);
  vec3 key = mix(S(240.0, 196.0, 104.0), S(255.0, 250.0, 232.0), u_tens);
  col = mix(col, key * (1.1 + 1.4 * u_tens + 0.4 * sin(u_time * 2.0)), hub);
  float frame = smoothstep(0.945, 0.965, r);
  col = mix(col, S(34.0, 36.0, 48.0), frame);
  x3d_FragColor = vec4(finish(col), 1.0);
}
