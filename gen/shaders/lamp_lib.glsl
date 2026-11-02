// The ring of 24 lanterns inside the arcade (radius 12.55, height 4.1, one per bay) lights every surface from its nearest four. Positions are analytic, so no uniform array.
uniform float u_lampI;
vec3 lamps(vec3 P, vec3 N) {
  const float SEG = TAU / 24.0;
  float a = atan(P.x, -P.z);
  if (a < 0.0) a += TAU;
  float k0 = floor(a / SEG - 0.5);
  float sum = 0.0;
  for (int j = -1; j <= 2; j++) {
    float k = mod(k0 + float(j) + 24.0, 24.0);
    float ang = (k + 0.5) * SEG;
    vec3 L = vec3(12.55 * sin(ang), 4.1, -12.55 * cos(ang)) - P;
    float d2 = dot(L, L);
    float lam = max(dot(N, L) * inversesqrt(d2), 0.0);
    float q = 1.0 + d2 / 13.0;
    sum += lam / (q * q);
  }
  return vec3(1.0, 0.64, 0.32) * sum * 2.5 * u_lampI;
}
