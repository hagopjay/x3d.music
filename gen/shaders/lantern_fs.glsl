//@include common
in vec3 v_nrm;
in vec3 v_pos;
in vec4 v_col;
flat in float v_ph;
in float v_glass;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 N = normalize(v_nrm);
  vec3 V = normalize(-v_pos);
  float fres = pow(1.0 - abs(dot(N, V)), 2.0);
  float fl = 0.93 + 0.07 * sin(u_time * 7.0 + v_ph * 6.28) + 0.03 * sin(u_time * 13.3 + v_ph * 17.0);
  vec3 glass = mix(vec3(1.0, 0.86, 0.5), vec3(1.0, 0.55, 0.2), fres) * 2.0 * fl;
  vec3 frame = v_col.rgb * 2.0 * (0.6 + 0.4 * abs(dot(N, V)));
  x3d_FragColor = vec4(finish(mix(frame, glass, v_glass)), 1.0);
}
