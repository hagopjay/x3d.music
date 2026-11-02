//@include common
//@include ode_lib
// A shaft of window light: soft across, fading along its length, drifting with slow noise, brighter and leaning in harmony with the tension.
in vec2 v_uv;
in vec3 v_world;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) discard;
  float across = pow(sin(PI * clamp(v_uv.x, 0.0, 1.0)), 1.6);
  float along = (1.0 - v_uv.y) * smoothstep(0.0, 0.08, v_uv.y);
  float n = 0.6 + 0.6 * fbm(vec2(v_uv.x * 3.0 + u_time * 0.03, v_uv.y * 2.0 - u_time * 0.05) + v_world.xz * 0.05);
  float a = across * along * n * (0.15 + 0.16 * u_tens + 0.07 * u_act) * (1.0 - 0.6 * u_calm);
  x3d_FragColor = vec4(vec3(0.62, 0.76, 1.0) * 1.6, clamp(a, 0.0, 0.5));
}
