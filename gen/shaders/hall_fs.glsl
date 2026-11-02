//@include common
//@include lamp_lib
uniform mat4 x3d_CameraSpaceMatrix;
uniform float u_key;
in vec3 v_world;
in vec3 v_nrm;
in vec3 v_col;
flat in float v_mat;
out vec4 x3d_FragColor;
// materials: 0 flagstone floor, 1 plaster and sandstone, 2 cool alcove wall, 3 brass and wood (plain vertex colour)
vec3 flagstones(vec3 P) {
  float r = length(P.xz);
  float row = floor(r / 0.62);
  float arc = atan(P.x, -P.z) * r;
  float u = arc / 1.25 + 0.5 * mod(row, 2.0);
  vec2 id = vec2(floor(u), row);
  vec2 f = vec2(fract(u), fract(r / 0.62));
  float joint = smoothstep(0.0, 0.035, min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y)));
  float tone = 0.7 + 0.5 * hash21(id) + 0.25 * (fbm(P.xz * 2.3) - 0.5);
  return vec3(0.62, 0.52, 0.40) * tone * (0.35 + 0.65 * joint);
}
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 N = normalize(v_nrm);
  vec3 V = normalize((x3d_CameraSpaceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz - v_world);
  if (dot(N, V) < 0.0) N = -N;
  int m = int(v_mat + 0.5);
  vec3 alb = v_col;
  float spec = 0.0;
  if (m == 0) { alb = flagstones(v_world); spec = 0.25; }
  else if (m == 1) {
    float n = fbm(v_world.xz * 1.7 + v_world.y * 2.1);
    alb = v_col * (0.8 + 0.4 * n);
    float course = smoothstep(0.0, 0.03, abs(fract(v_world.y / 0.55) - 0.5) - 0.47 + 0.03);
    alb *= 0.82 + 0.18 * course;
  } else if (m == 2) { alb = v_col * (0.8 + 0.4 * fbm(v_world.xy * 1.3 + v_world.zz)); }
  else if (m == 4) {
    // the hub: a brass medallion with a twelve-pointed star in cobalt and tomato, breathing on the beat
    vec2 p = v_world.xz / 1.38;
    float r = length(p);
    float a = atan(p.x, -p.y);
    float pt = 0.34 + 0.6 * pow(abs(cos(6.0 * a)), 3.0);
    float inStar = smoothstep(0.02, -0.02, r - pt * 0.9);
    vec3 st = mod(floor(a / (TAU / 12.0) + 0.5), 2.0) < 0.5 ? S(20.0, 60.0, 150.0) : S(190.0, 52.0, 36.0);
    alb = mix(v_col, st, inStar);
    alb = mix(alb, v_col * 1.3, smoothstep(0.03, 0.0, abs(r - 0.96) - 0.02));
    alb = mix(alb, S(240.0, 200.0, 120.0), smoothstep(0.1, 0.07, r));
    spec = 0.6;
  }
  vec3 amb = vec3(0.03, 0.045, 0.095) * (0.5 + 0.5 * N.y) + vec3(0.05, 0.035, 0.02);
  vec3 L = lamps(v_world, N);
  vec3 col = alb * (amb + L);
  if (m == 4) col += alb * vec3(1.0, 0.7, 0.35) * 0.35 * (0.6 + 0.6 * exp(-fract(u_time * 2.1) * 4.0)) * (1.0 - 0.8 * u_calm);
  vec3 H = normalize(V + vec3(0.0, 1.0, 0.0));
  col += spec * L * pow(max(dot(N, H), 0.0), 18.0);
  x3d_FragColor = vec4(finish(col), 1.0);
}
