//@include common
in vec2 v_c;
in vec3 v_rgb;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) discard;
  float r2 = dot(v_c, v_c);
  float a = exp(-r2 * 4.5) * (1.0 - smoothstep(0.6, 1.0, r2));
  x3d_FragColor = vec4(finish(v_rgb * 1.5), clamp(a * 0.55, 0.0, 1.0));
}
