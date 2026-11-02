// Light in the nave. The tapestry's own warm glow is the main lamp (it swells with the note activity), cool window light comes from above and a little from the sides.
uniform float u_act;
uniform float u_tens;

vec3 ink(float i) {
  if (i < 0.5) return S(62.0, 74.0, 178.0);
  if (i < 1.5) return S(204.0, 212.0, 228.0);
  if (i < 2.5) return S(246.0, 192.0, 82.0);
  if (i < 3.5) return S(250.0, 244.0, 226.0);
  return S(224.0, 42.0, 62.0);
}

vec3 naveLight(vec3 P, vec3 N) {
  vec3 c = vec3(0.018, 0.030, 0.068) * (0.6 + 0.4 * N.y);
  vec3 d = vec3(0.0, 6.5, -22.0) - P;
  float d2 = dot(d, d);
  float att = 1.0 / (1.0 + d2 * 0.0075);
  float lam = max(dot(N, d * inversesqrt(d2)), 0.0);
  c += vec3(1.0, 0.80, 0.52) * (0.35 + 1.3 * u_act) * att * lam * 1.7;
  vec3 e = vec3(0.0, 12.5, -16.0) - P;
  float e2 = dot(e, e);
  c += vec3(1.0, 0.78, 0.50) * 1.1 / (1.0 + e2 * 0.025) * max(dot(N, e * inversesqrt(e2)), 0.0);
  vec3 w = normalize(vec3(-sign(P.x) * 0.45, 0.85, 0.1));
  float win = max(dot(N, w), 0.0) * smoothstep(2.0, 16.0, P.y);
  c += vec3(0.30, 0.44, 0.80) * win * (0.34 + 0.5 * u_tens);
  return c;
}
