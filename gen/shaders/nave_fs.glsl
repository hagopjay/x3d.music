//@include common
//@include ode_lib
uniform mat4 x3d_CameraSpaceMatrix;
uniform float u_layer;
in vec3 v_world;
in vec3 v_nrm;
in vec3 v_col;
flat in float v_mat;
out vec4 x3d_FragColor;
// materials: 0 polished floor, 1 stone, 2 vault, 3 brass, 4 bronze, 5 wood, 6 window glass (lit from outside), 7 steel, 8 bobbin (the colour of the layer being laid), 9 reading bar, 10 wall
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 P = v_world;
  vec3 N = normalize(v_nrm);
  vec3 V = normalize((x3d_CameraSpaceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz - P);
  if (dot(N, V) < 0.0) N = -N;
  int m = int(v_mat + 0.5);
  vec3 alb = v_col;
  float spec = 0.0, gloss = 24.0;
  vec3 emit = vec3(0.0);
  vec3 refl = vec3(0.0);
  if (m == 0) {
    vec2 g = P.xz / 1.6;
    vec2 id = floor(g);
    vec2 f = fract(g);
    float joint = smoothstep(0.0, 0.025, min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y)));
    alb = S(30.0, 33.0, 44.0) * (0.75 + 0.5 * hash21(id)) * (0.35 + 0.65 * joint);
    spec = 1.0; gloss = 90.0;
    // the tapestry mirrored in the polished stone: a soft streak down the middle of the nave
    vec3 R = reflect(-V, N);
    if (R.z < -0.001) {
      float t = (-23.8 - P.z) / R.z;
      vec3 h = P + R * t;
      float inx = smoothstep(6.5, 1.5, abs(h.x));
      float iny = smoothstep(-1.0, 3.5, h.y) * smoothstep(15.0, 7.0, h.y);
      float fres = 0.04 + 0.70 * pow(1.0 - max(dot(N, V), 0.0), 3.0);
      vec3 tone = mix(vec3(0.16, 0.20, 0.55), vec3(1.0, 0.72, 0.36), clamp(u_layer / 3.0, 0.0, 1.0));
      refl = tone * inx * iny * fres * (0.35 + 1.1 * u_act);
    }
  } else if (m == 1 || m == 10) {
    float n = fbm(P.xy * 0.9 + P.zz * 0.7);
    float course = smoothstep(0.0, 0.04, abs(fract(P.y / 0.7) - 0.5) - 0.46 + 0.04);
    alb = v_col * (0.72 + 0.5 * n) * (0.78 + 0.22 * course);
    spec = 0.12;
  } else if (m == 2) {
    float rib = smoothstep(0.0, 0.07, abs(fract(P.z / 6.5 + 0.5) - 0.5) - 0.025);
    alb = v_col * (0.8 + 0.4 * fbm(P.xz * 0.6)) * (0.55 + 0.45 * rib);
    spec = 0.0;
  } else if (m == 6) {
    float mull = smoothstep(0.0, 0.05, abs(fract(P.z / 1.05) - 0.5) - 0.455);
    float tra = smoothstep(0.0, 0.05, abs(fract(P.y / 1.6 + 0.3) - 0.5) - 0.47);
    alb = vec3(0.02);
    emit = vec3(0.46, 0.62, 1.0) * 2.4 * (0.25 + 0.75 * mull * tra) * (0.85 + 0.35 * u_tens);
  } else if (m == 3) { spec = 0.9; gloss = 48.0; alb = v_col; }
  else if (m == 4) { spec = 0.5; gloss = 30.0; alb = v_col; }
  else if (m == 5) { alb = v_col * (0.8 + 0.4 * fbm(vec2(P.x * 3.0 + P.z * 3.0, P.y * 0.6))); spec = 0.18; }
  else if (m == 7) { spec = 1.0; gloss = 80.0; alb = v_col; }
  else if (m == 8) { alb = vec3(0.02); emit = ink(u_layer) * (2.2 + 0.5 * sin(u_time * 9.0)); }
  else if (m == 9) { alb = vec3(0.02); emit = S(255.0, 214.0, 150.0) * (2.6 + 0.4 * sin(u_time * 5.0)); }
  vec3 L = naveLight(P, N);
  float metal = (m == 3 || m == 4 || m == 7) ? 0.62 : 1.0;
  vec3 col = alb * L * metal + emit + refl;
  vec3 Lt = normalize(vec3(0.0, 6.5, -22.0) - P);
  vec3 H = normalize(V + Lt);
  col += spec * vec3(1.0, 0.82, 0.58) * (0.2 + 0.8 * u_act) * pow(max(dot(N, H), 0.0), gloss) * 1.4;
  vec3 Hw = normalize(V + normalize(vec3(-sign(P.x) * 0.45, 0.85, 0.1)));
  col += spec * vec3(0.4, 0.55, 1.0) * 0.5 * pow(max(dot(N, Hw), 0.0), gloss);
  x3d_FragColor = vec4(finish(col), 1.0);
}
