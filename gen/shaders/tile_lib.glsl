// Iznik tile art, procedural: a rosette field with a white inline and a cobalt border. Colours are linear (already through S()).
vec3 tileArt(vec2 uv, float seed, float petals, vec3 c1, vec3 c2, vec3 c3, vec3 c4) {
  vec2 p = uv * 2.0 - 1.0;
  float d = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  float r = length(p);
  float a = atan(p.y, p.x) + seed * 0.9;
  vec3 col = c2;
  // four carnations in the corners: a tomato bud inside a cobalt leaf
  vec2 q = abs(p) - vec2(0.80);
  float cr = length(q);
  col = mix(col, c1, smoothstep(0.30, 0.27, cr));
  col = mix(col, c4, smoothstep(0.17, 0.14, cr));
  // the rosette: petals in tomato, a white disc, a cobalt ring, a turquoise heart
  float petal = 0.33 + 0.42 * pow(0.5 + 0.5 * cos(petals * a), 1.6);
  col = mix(col, c4, smoothstep(petal + 0.02, petal - 0.02, r));
  col = mix(col, c3, smoothstep(0.30, 0.27, r));
  col = mix(col, c1, smoothstep(0.020, 0.008, abs(r - 0.23)));
  col = mix(col, c2, smoothstep(0.12, 0.10, r));
  // border: cobalt band, white inline
  col = mix(col, c1, smoothstep(0.075, 0.068, d));
  col = mix(col, c3, smoothstep(0.014, 0.008, abs(d - 0.092)));
  // glaze: a slow mottling, a little craquelure
  float g = fbm(uv * 7.0 + seed * 3.1);
  col *= 0.88 + 0.22 * g;
  col *= 1.0 - 0.25 * smoothstep(0.78, 0.9, vnoise(uv * 23.0 + seed));
  return col;
}

// The three palettes of the piece (the key map): A minor cobalt and turquoise, A major tomato and gold, F# minor green and turquoise. k in 0..2 blends between them.
void palette(float k, out vec3 c1, out vec3 c2, out vec3 c3, out vec3 c4) {
  vec3 a1 = S(14.0, 52.0, 140.0), a2 = S(24.0, 156.0, 156.0), a4 = S(190.0, 52.0, 36.0);
  vec3 b1 = S(196.0, 58.0, 40.0), b2 = S(226.0, 172.0, 64.0), b4 = S(20.0, 60.0, 150.0);
  vec3 g1 = S(22.0, 112.0, 78.0), g2 = S(24.0, 156.0, 156.0), g4 = S(20.0, 60.0, 150.0);
  float k1 = clamp(k, 0.0, 1.0), k2 = clamp(k - 1.0, 0.0, 1.0);
  c1 = mix(mix(a1, b1, k1), g1, k2);
  c2 = mix(mix(a2, b2, k1), g2, k2);
  c4 = mix(mix(a4, b4, k1), g4, k2);
  c3 = S(232.0, 226.0, 208.0);
}

// Twelve glass colours for the twelve pitch classes, laid on the circle of fifths so neighbouring fifths are neighbouring hues (sRGB bytes).
const vec3 WHEEL[12] = vec3[12](vec3(214.0, 62.0, 40.0), vec3(236.0, 118.0, 42.0), vec3(240.0, 176.0, 56.0), vec3(246.0, 214.0, 110.0), vec3(248.0, 240.0, 214.0), vec3(150.0, 226.0, 214.0),
                                vec3(40.0, 190.0, 184.0), vec3(30.0, 140.0, 210.0), vec3(50.0, 90.0, 220.0), vec3(110.0, 80.0, 205.0), vec3(214.0, 90.0, 150.0), vec3(190.0, 40.0, 70.0));
vec3 wheel(int i) { vec3 c = WHEEL[i]; return S(c.x, c.y, c.z); }
