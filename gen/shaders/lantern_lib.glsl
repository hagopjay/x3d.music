// Lanterns swing a little on the beat. q = quarters since the start, from the constant tempo u_qpm (the Rondo has one tempo).
uniform float u_qpm;
vec3 sway(vec3 p, vec3 anchor, float ph) {
  float q = u_time * u_qpm / 60.0;
  float a = 0.07 * sin(q * PI + ph) * (1.0 - 0.8 * u_calm);
  float b = 0.05 * cos(q * PI * 0.5 + ph * 1.7) * (1.0 - 0.8 * u_calm);
  vec3 r = p - anchor;
  r = vec3(r.x * cos(b) - r.y * sin(b), r.x * sin(b) + r.y * cos(b), r.z);
  r = vec3(r.x, r.y * cos(a) - r.z * sin(a), r.y * sin(a) + r.z * cos(a));
  return anchor + r;
}
