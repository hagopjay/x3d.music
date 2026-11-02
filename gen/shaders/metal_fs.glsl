//@include common
//@include metal_lib
out vec4 x3d_FragColor;
void main() {
  if (u_idpass > 0.5) { x3d_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  x3d_FragColor = vec4(finish(shadeMetal()), 1.0);
}
