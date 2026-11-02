//@include common
//@include metal_lib
flat in vec4 v_glow;
flat in vec2 v_lit;
in float v_along;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(v_lit.x > 0.5 ? idColor(v_lit.y) : vec3(0.0), 1.0); return; }
  float core = exp(-max(v_glow.z, 0.0) * 6.0) * v_glow.x * (1.0 - 0.8 * u_calm);
  vec3 hot = mix(vec3(1.0, 0.55, 0.2), vec3(1.0, 0.95, 0.8), clamp(core * 1.2, 0.0, 1.0));
  float tip = smoothstep(0.35, 1.0, v_along);
  vec3 col = shadeMetal() + hot * v_glow.x * (0.5 + 1.6 * tip) + hot * core * 1.2 * tip;
  x3d_FragColor = vec4(finish(col), 1.0);
}
