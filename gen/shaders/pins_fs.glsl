//@include common
//@include metal_lib
flat in vec4 v_glow;
flat in vec2 v_lit;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(v_lit.x > 0.5 ? idColor(v_lit.y) : vec3(0.0), 1.0); return; }
  float core = exp(-max(v_glow.z, 0.0) * 6.0) * v_glow.x * (1.0 - 0.8 * u_calm);
  vec3 hot = mix(vec3(1.0, 0.5, 0.16), vec3(1.0, 0.93, 0.75), clamp(core * 1.2, 0.0, 1.0));
  vec3 col = shadeMetal() + vec3(1.0, 0.5, 0.14) * 0.1 + hot * (v_glow.x * 1.9 + core * 2.2);
  x3d_FragColor = vec4(finish(col), 1.0);
}
