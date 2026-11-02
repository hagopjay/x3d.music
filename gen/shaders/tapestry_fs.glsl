//@include common
//@include ode_lib
// The tapestry: 256 warp threads by 384 weft rows. u_cells holds the picture (three cell bytes per texel: code in bits 0 to 2, 0 = bare, 1..5 = the five threads, tone in bits 3 to 7).
// u_weave holds, for every layer and row, the notes sounding at the moment that row is woven (EventTable rows layer * 384 + row). A cell is owned by one of them, picked by an integer hash of the
// cell (hash2u, the same arithmetic in witnesses and the page, so no GPU's float rounding can change the owner); it appears when its row is woven (u_sweepA and u_sweepB give each statement's start and end) and glows for as long as its owner sounds, then settles.
uniform sampler2D u_cells;
uniform sampler2D u_weave;
uniform vec4 u_sweepA;
uniform vec4 u_sweepB;
in vec2 v_uv;
in vec3 v_obj;
out vec4 x3d_FragColor;
uint hash2u(ivec2 p) {
  uint h = uint(p.x) * 374761393u + uint(p.y) * 668265263u;
  h = (h ^ (h >> 13u)) * 1274126177u;
  return h ^ (h >> 16u);
}
float cellByte(ivec2 cell) {
  vec4 t = texelFetch(u_cells, ivec2(cell.x / 3, cell.y), 0);
  int c = cell.x - 3 * (cell.x / 3);
  float v = c == 0 ? t.r : (c == 1 ? t.g : t.b);
  return floor(v * 255.0 + 0.5);
}
void main() {
  vec2 g = vec2(v_uv.x * 256.0, v_uv.y * 384.0);
  ivec2 cell = ivec2(clamp(floor(g), vec2(0.0), vec2(255.0, 383.0)));
  vec2 f = g - vec2(cell);
  int byt = int(cellByte(cell));
  int code = byt & 7;
  float tone = float(byt >> 3) / 31.0;
  bool woven = false;
  float glow = 0.0;
  vec2 strict = vec2(0.0);
  if (code > 0) {
    int L = code - 1;
    int sw = min(L, 3);
    float t0 = u_sweepA[sw], t1 = u_sweepB[sw];
    float tw = t0 + (float(cell.y) + 0.5) / 384.0 * (t1 - t0);
    Row r = rowOf(u_weave, L * 384 + cell.y);
    if (r.n > 0 && u_time >= tw) {
      int k = int(hash2u(cell) % uint(r.n));
      Ev e = evAt(u_weave, r, k);
      woven = true;
      float a = clamp((u_time - e.on) / 0.10, 0.0, 1.0);
      a = a * a * (3.0 - 2.0 * a);
      glow = a * (u_time <= e.off ? 1.0 : exp(-(u_time - e.off) / 0.9));
      if (u_time >= e.on && u_time <= e.off) strict = vec2(1.0, e.id);
    }
  }
  if (u_idpass > 0.5) { x3d_FragColor = vec4(strict.x > 0.5 ? idColor(strict.y) : vec3(0.0), 1.0); return; }
  float px = fwidth(g.y);
  float lod = smoothstep(0.30, 0.80, px);
  float prof = sin(PI * clamp((f.y - 0.04) / 0.92, 0.0, 1.0));
  float weft = mix(0.5 + 0.55 * prof, 0.9, lod);
  float gap = mix(smoothstep(0.0, 0.09, f.y) * smoothstep(1.0, 0.91, f.y), 1.0, lod);
  float wx = abs(f.x - 0.5);
  float warp = mix(smoothstep(0.36, 0.20, wx), 0.55, lod);
  vec3 linen = S(214.0, 200.0, 170.0);
  vec3 bare = linen * (0.30 + 0.40 * fbm(vec2(g.x * 0.7, g.y * 0.05))) * warp * 0.45 + vec3(0.004, 0.005, 0.010);
  vec3 col = bare;
  if (woven) {
    vec3 c = ink(float(code - 1));
    vec3 thread = c * mix(0.32, 1.15, tone) * weft;
    col = mix(bare * 0.6, thread, gap);
    col *= 0.94 + 0.06 * mod(float(cell.x + cell.y), 2.0);
    col += c * glow * (1.0 - 0.8 * u_calm) * 2.0 * (0.45 + 0.55 * prof);
  }
  float fr = -1.0;
  for (int i = 0; i < 4; i++) {
    if (u_time >= u_sweepA[i] && u_time <= u_sweepB[i]) fr = (u_time - u_sweepA[i]) / (u_sweepB[i] - u_sweepA[i]) * 384.0;
  }
  if (fr >= 0.0) {
    float d = g.y - fr;
    col += S(255.0, 214.0, 150.0) * (exp(-abs(d) * 0.9) * 1.1 + exp(-abs(d) * 0.08) * 0.10);
  }
  vec2 q = v_uv - 0.5;
  float vig = 1.0 - 0.35 * dot(q, q) * 2.0;
  col *= (0.55 + 0.55 * u_act) * vig;
  x3d_FragColor = vec4(finish(col), 1.0);
}
