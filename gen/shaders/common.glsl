// Loomsong shader library, shared by every world shader (vertex and fragment). GLSL ES 3.00.
// Standard uniforms, set by the page and by the generator: u_time seconds on the performance clock (ROUTEd from SecondsBus), u_dur the piece length D,
// u_idpass 1 draws note-id colours instead of the picture (the Sync witness), u_calm 1 cuts glow pulses by 80 percent.
uniform float u_time;
uniform float u_dur;
uniform float u_idpass;
uniform float u_calm;

#define TAU 6.28318530718
#define PI 3.14159265359

float hash11(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash21(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 hash22(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973)); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x), mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), f.x), f.y);
}
float fbm(vec2 p) {
  float a = 0.5, s = 0.0;
  for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; }
  return s;
}

// Colours are written as sRGB bytes and worked on in linear light; finish() tone-maps and gamma-encodes the result.
vec3 S(float r, float g, float b) { return pow(vec3(r, g, b) * (1.0 / 255.0), vec3(2.2)); }
vec3 finish(vec3 lin) {
  lin *= 0.9;
  vec3 m = clamp((lin * (2.51 * lin + 0.03)) / (lin * (2.43 * lin + 0.59) + 0.14), 0.0, 1.0);
  return pow(m, vec3(1.0 / 2.2));
}
// A 24-bit note id as an RGB colour (id + 1, so black means no note). Written untouched in the id pass.
vec3 idColor(float id) { float v = id + 1.0; return vec3(mod(v, 256.0), mod(floor(v / 256.0), 256.0), floor(v / 65536.0)) / 255.0; }

// ---- event rows (EventTable in gen/worldlib.py) ----
// One texel stream wrapped at 1024. Texel 0 = B, where the events begin; row r: first event at texel 1 + 2r, count at 2 + 2r; event j = texels B + 4j .. B + 4j + 3.
float byte1(float c) { return floor(c * 255.0 + 0.5); }
ivec2 tx(int i) { return ivec2(i & 1023, i >> 10); }
int rd24(sampler2D tex, int i) { vec4 e = texelFetch(tex, tx(i), 0); return int(byte1(e.r)) * 65536 + int(byte1(e.g)) * 256 + int(byte1(e.b)); }
float time24(vec4 e) { return (byte1(e.r) * 65536.0 + byte1(e.g) * 256.0 + byte1(e.b)) * (u_dur / 16777215.0); }

struct Row { int base; int n; };
struct Ev { float on; float off; float vel; float aux; float kind; float id; };

Row rowOf(sampler2D tex, int row) {
  Row r;
  r.base = rd24(tex, 0) + 4 * rd24(tex, 1 + 2 * row);
  r.n = rd24(tex, 2 + 2 * row);
  return r;
}
float evOn(sampler2D tex, Row r, int i) { return time24(texelFetch(tex, tx(r.base + 4 * i), 0)); }
Ev evAt(sampler2D tex, Row r, int i) {
  Ev e;
  int k = r.base + 4 * i;
  e.on = time24(texelFetch(tex, tx(k), 0));
  e.off = time24(texelFetch(tex, tx(k + 1), 0));
  vec4 c = texelFetch(tex, tx(k + 2), 0);
  e.vel = c.r; e.aux = byte1(c.g); e.kind = byte1(c.b);
  e.id = float(rd24(tex, k + 3));
  return e;
}

// Index of the last event in the row with t_on <= t, or -1.
int lastOn(sampler2D tex, Row r, float t) {
  int lo = 0, hi = r.n;
  for (int s = 0; s < 16; s++) {
    if (lo >= hi) break;
    int mid = (lo + hi) / 2;
    if (evOn(tex, r, mid) <= t) lo = mid + 1; else hi = mid;
  }
  return lo - 1;
}

// Glow of a row at time t. x envelope 0..1 (a smoothstep ramp of `attack` seconds from t_on, then an exponential settle of `tau` seconds after t_off),
// y velocity 0..1, z seconds since the strongest event began, w its kind. Looks back over the last three events, since quick repeats overlap.
vec4 glowAt(sampler2D tex, int row, float t, float attack, float tau) {
  vec4 best = vec4(0.0);
  Row r = rowOf(tex, row);
  if (r.n == 0) return best;
  int k = lastOn(tex, r, t);
  for (int j = 0; j < 3; j++) {
    int i = k - j;
    if (i < 0) break;
    Ev e = evAt(tex, r, i);
    float a = clamp((t - e.on) / attack, 0.0, 1.0);
    a = a * a * (3.0 - 2.0 * a);
    float env = a * (t <= e.off ? 1.0 : exp(-(t - e.off) / tau));
    if (env > best.x) best = vec4(env, e.vel, t - e.on, e.kind);
  }
  return best;
}

// The strict window for the id pass: x = 1 while some event of the row has t_on <= t <= t_off, y = that note's id.
vec2 litStrict(sampler2D tex, int row, float t) {
  Row r = rowOf(tex, row);
  if (r.n == 0) return vec2(0.0, 0.0);
  int k = lastOn(tex, r, t);
  for (int j = 0; j < 3; j++) {
    int i = k - j;
    if (i < 0) break;
    Ev e = evAt(tex, r, i);
    if (t >= e.on && t <= e.off) return vec2(1.0, e.id);
  }
  return vec2(0.0, 0.0);
}
