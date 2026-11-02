//@include common
//@include tile_lib
//@include lamp_lib
uniform float u_key;
in vec3 v_world;
in vec2 v_uv;
flat in float v_tile;
flat in vec4 v_glow;
flat in vec2 v_lit;
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(v_lit.x > 0.5 ? idColor(v_lit.y) : vec3(0.0), 1.0); return; }
  int tile = int(v_tile + 0.5);
  int ring = tile / 12;
  int sector = tile - ring * 12;
  vec3 c1, c2, c3, c4;
  palette(u_key, c1, c2, c3, c4);
  vec2 uv = v_uv;
  float d = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  float seed = float(tile) * 1.618;
  vec3 base = tileArt(uv, seed, 6.0 + 2.0 * float(ring - (ring / 2) * 2), c1, c2, c3, c4);
  float mortar = smoothstep(0.0, 0.03, d);
  vec3 tint = wheel(sector);
  float env = v_glow.x * (0.55 + 0.45 * v_glow.y);
  float core = exp(-max(v_glow.z, 0.0) * 7.0) * v_glow.x * (1.0 - 0.8 * u_calm);
  float inner = 1.0 - smoothstep(0.0, 0.8, length(uv * 2.0 - 1.0));
  float r = length(v_world.xz);
  vec3 lamp = vec3(0.05, 0.035, 0.02) + lamps(v_world, vec3(0.0, 1.0, 0.0)) * 0.7 + vec3(1.0, 0.72, 0.45) * 0.07 * smoothstep(9.0, 3.0, r);
  vec3 col = base * lamp * mortar * 0.62;
  vec3 glass = mix(base * 0.7, tint, 0.62) * (0.9 + 1.5 * inner);
  col += glass * env * 1.7 * (0.35 + 0.65 * mortar) + tint * core * 1.1 * mortar;
  col += tint * env * 0.35 * (1.0 - mortar);
  x3d_FragColor = vec4(finish(col), 1.0);
}
