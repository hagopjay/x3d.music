//@include common
//@include ode_lib
// The card chain, laid out like a piano roll: one card for each beat (0.12 m), one hole for each note, where it begins in the beat and as long as it lasts. Holes sound as they pass the reading bar at x = 0.
in vec3 v_world;
in vec2 v_loc;
flat in float v_kind;
flat in vec4 v_ev;
flat in float v_fam;
out vec4 x3d_FragColor;
void main() {
  float fade = 1.0 - smoothstep(7.5, 10.5, abs(v_world.x));
  if (v_kind > 0.5) {
    float t0 = v_ev.y, t1 = v_ev.z;
    float on = (u_time >= t0 && u_time <= t1) ? 1.0 : 0.0;
    if (u_idpass > 0.5) { x3d_FragColor = vec4(on > 0.5 ? idColor(v_ev.x) : vec3(0.0), 1.0); return; }
    float a = clamp((u_time - t0) / 0.05, 0.0, 1.0);
    float env = a * (u_time <= t1 ? 1.0 : exp(-(u_time - t1) / 0.7));
    vec3 c = ink(v_fam);
    vec3 col = vec3(0.004, 0.005, 0.012) + c * (0.07 + 2.6 * env * (1.0 - 0.7 * u_calm));
    x3d_FragColor = vec4(finish(col * fade), 1.0);
    return;
  }
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  float cx = fract(v_loc.x / 0.12);
  float seam = smoothstep(0.0, 0.045, min(cx, 1.0 - cx));
  float y = v_loc.y;
  float rail = smoothstep(0.90, 0.93, abs(y));
  float stud = rail * smoothstep(0.30, 0.22, length(vec2(cx - 0.5, (abs(y) - 0.965) * 2.6)));
  float grain = 0.8 + 0.4 * fbm(vec2(v_loc.x * 9.0, y * 5.0));
  vec3 plate = S(108.0, 96.0, 78.0) * grain;
  plate = mix(plate, S(150.0, 128.0, 92.0), rail * 0.8);
  plate += S(255.0, 220.0, 150.0) * stud * 0.6;
  float bar = exp(-pow(v_world.x * 5.0, 2.0));
  vec3 L = vec3(0.04, 0.05, 0.10) + vec3(1.0, 0.8, 0.5) * (0.12 + 0.35 * u_act + 0.55 * bar);
  vec3 col = plate * L * (0.25 + 0.75 * seam);
  x3d_FragColor = vec4(finish(col * fade), 1.0);
}
