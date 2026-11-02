//@include common
in vec2 v_c;
flat in vec4 v_glow;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) discard;
  float r2 = dot(v_c, v_c);
  float core = exp(-max(v_glow.z, 0.0) * 6.0) * v_glow.x * (1.0 - 0.8 * u_calm);
  float a = exp(-r2 * 5.0) * v_glow.x * (0.55 + 0.45 * v_glow.y) * (1.0 - smoothstep(0.7, 1.0, r2));
  vec3 col = mix(vec3(1.0, 0.52, 0.18), vec3(1.0, 0.9, 0.62), clamp(core + exp(-r2 * 24.0) * 0.6, 0.0, 1.0));
  x3d_FragColor = vec4(finish(col * 1.6), clamp(a * 0.85, 0.0, 1.0));
}
