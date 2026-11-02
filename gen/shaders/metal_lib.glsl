// Surfaces lit by the lantern ring, with a mirror-ish sheen: stone, brass, steel, porcelain. The vertex Color is the albedo (stored at half strength, meshlib.COLOR_GAIN) when u_vcol is 1;
// otherwise u_albedo is. u_flat 1 takes the normal from screen derivatives (pins, teeth: no Normal array in the file). Lighting is analytic (lamp_lib), so nothing here is baked.
//@include lamp_lib
uniform mat4 x3d_CameraSpaceMatrix;
uniform vec3 u_envTop;
uniform vec3 u_envHor;
uniform vec3 u_envLow;
uniform vec3 u_tint;
uniform vec3 u_albedo;
uniform float u_ring;
uniform float u_gloss;
uniform float u_brushed;
uniform float u_vcol;
uniform float u_flat;
in vec3 v_nrm;
in vec3 v_pos;
in vec4 v_col;
in vec3 v_obj;

vec3 envOf(vec3 d) {
  float h = d.y;
  vec3 c = mix(u_envHor, u_envTop, smoothstep(0.0, 0.9, h));
  c = mix(c, u_envLow, smoothstep(0.0, -0.4, h));
  float az = atan(d.z, d.x);
  float ring = pow(0.5 + 0.5 * cos(az * 24.0), 10.0) * smoothstep(-0.1, 0.25, h) * smoothstep(0.75, 0.25, h);
  return c + vec3(1.0, 0.62, 0.28) * ring * u_ring;
}

vec3 shadeMetal() {
  vec3 V = normalize(-v_pos);
  vec3 N = u_flat > 0.5 ? normalize(cross(dFdx(v_pos), dFdy(v_pos))) : normalize(v_nrm);
  if (dot(N, V) < 0.0) N = -N;
  vec3 Nw = normalize((x3d_CameraSpaceMatrix * vec4(N, 0.0)).xyz);
  vec3 Pw = (x3d_CameraSpaceMatrix * vec4(v_pos, 1.0)).xyz;
  float ndv = max(dot(N, V), 0.0);
  vec3 Rw = normalize((x3d_CameraSpaceMatrix * vec4(reflect(-V, N), 0.0)).xyz);
  float fres = 0.08 + 0.92 * pow(1.0 - ndv, 5.0);
  float streak = 1.0;
  if (u_brushed > 0.0) streak = 0.8 + 0.4 * vnoise(vec2(v_obj.x * 70.0, atan(v_obj.y, v_obj.z) * 45.0));
  vec3 albedo = u_vcol > 0.5 ? v_col.rgb * 2.0 : u_albedo;
  vec3 amb = vec3(0.035, 0.05, 0.10) * (0.6 + 0.4 * Nw.y) + vec3(0.05, 0.035, 0.02);
  vec3 key = vec3(1.0, 0.7, 0.42) * 0.22 * max(dot(Nw, normalize(vec3(-0.35, 0.55, 0.75))), 0.0);
  vec3 diff = albedo * (amb + key + lamps(Pw, Nw));
  vec3 spec = envOf(Rw) * u_tint * (u_gloss * (0.3 + 0.7 * fres)) * streak;
  return diff * (1.0 - 0.25 * u_gloss) + spec;
}
