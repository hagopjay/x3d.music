#!/usr/bin/env python3
"""P0 probe assets, written to build/probes/. Each probe answers one question the spec marks S until it is run.

  probe_a.x3d          time bus (FractionBus -> SecondsBus -> shader u_time), per-vertex attributes, a nearest-filtered data texture
  probe_splat41.x3d    one small X3D 4.1 GaussianSplats node with bboxSize and bboxCenter set
  probe_splat40_bad.x3d  the same node declared as 4.0 (the version-fits-nodes trap: the validator must refuse it)
  click.{mp4,ogg,mp3,wav}  a master-shaped file with two bursts at exactly 1.000 s and 2.000 s, for the audio decode and clock probes
  index.html           the probe page (an HTML fragment: the host wraps it in its skeleton)
"""
import json, math, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from x3dw import N, Node, document, mf, num, route, shader, time_bus   # noqa: E402

OUT = os.path.join(HERE, "..", "..", "build", "probes")
D = 230.0                      # a piece-length duration, so the 16-bit time texture has its real resolution (3.5 ms)
STRIPS = 8

VS = """#version 300 es
precision highp float;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in float a_tOn;
in float a_k;
out float v_tOn;
flat out float v_k;
void main() {
  v_tOn = a_tOn; v_k = a_k;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
"""
FS = """#version 300 es
precision highp float; precision highp int;
uniform float u_time;
uniform float u_dur;
uniform sampler2D u_events;
in float v_tOn;
flat in float v_k;
out vec4 x3d_FragColor;
void main() {
  float litAttr = step(v_tOn, u_time);
  vec4 e = texelFetch(u_events, ivec2(int(v_k + 0.5), 0), 0) * 255.0;
  float texT = (e.r * 256.0 + e.g) / 65535.0 * u_dur;
  float litTex = step(texT - 0.004, u_time);
  float near = texture(u_events, vec2((v_k + 0.95) / 8.0, 0.5)).b;     // 0.45 texel off centre: exactly 0 or 1 only if NEAREST is honoured
  x3d_FragColor = vec4(litAttr, litTex, near, 1.0);
}
"""


def probe_a():
    ev = []
    for k in range(STRIPS):
        t_on = k * D / STRIPS
        v = round(t_on / D * 65535)
        ev.append("0x%02X%02X%02X%02X" % (v >> 8, v & 255, 255 if k % 2 else 0, 255))      # R,G = 16-bit time; B = parity marker; A opaque
    tex = N("PixelTexture", N("TextureProperties", containerField="textureProperties", generateMipMaps=False, magnificationFilter="NEAREST_PIXEL",
                              minificationFilter="NEAREST_PIXEL", boundaryModeS="CLAMP_TO_EDGE", boundaryModeT="CLAMP_TO_EDGE"),
            image="%d 1 4 %s" % (STRIPS, " ".join(ev)), repeatS=False, repeatT=False)
    pts, idx, a_t, a_k = [], [], [], []
    for k in range(STRIPS):
        x0 = -2 + 0.5 * k
        base = 4 * k
        pts += [x0, 0, 0, x0 + 0.5, 0, 0, x0 + 0.5, 1, 0, x0, 1, 0]
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
        a_t += [k * D / STRIPS] * 4
        a_k += [float(k)] * 4
    sh = shader("Sh", [("u_time", "SFFloat", "inputOutput", 0), ("u_dur", "SFFloat", "inputOutput", D), ("u_events", "SFNode", "inputOutput", tex)], VS, FS)
    geom = N("IndexedTriangleSet", N("Coordinate", point=mf(pts)), N("FloatVertexAttribute", name="a_tOn", numComponents=1, value=mf(a_t, 3)),
             N("FloatVertexAttribute", name="a_k", numComponents=1, value=mf(a_k, 1)), index=" ".join(map(str, idx)), solid=False)
    kids = [N("OrthoViewpoint", DEF="Cam", position="0 0.5 5", fieldOfView="-2.1333 -1.2 2.1333 1.2", description="probe"),
            N("NavigationInfo", type='"NONE"', headlight=False),
            N("Background", skyColor="0 0 0")]
    kids += time_bus(D)
    kids += [N("TimeSensor", DEF="Clock", cycleInterval=D, loop=True, enabled=False),
             N("Shape", N("Appearance", sh), geom),
             route("Clock", "fraction_changed", "FractionBus", "set_fraction"),
             route("SecondsBus", "value_changed", "Sh", "u_time")]
    return document(kids, components=[("Interpolation", 2), ("Navigation", 3), ("Shaders", 1), ("Texturing", 2), ("Time", 1)],
                    title="Loomsong probe A", description="Time bus, per-vertex attributes and a nearest-filtered data texture", generator="loomsong gen/probes/make_probes.py")


def splat_scene(version):
    pos, scl, ori, opa, sh0 = [], [], [], [], []
    c0 = 0.28209479177387814
    for i in range(3):
        for j in range(3):
            for k in range(3):
                pos += [(i - 1) * 0.5, (j - 1) * 0.5, (k - 1) * 0.5]
                scl += [0.12, 0.12, 0.12]
                ori += [0, 0, 0, 1]
                opa += [0.9]
                col = [0.25 + 0.5 * i / 2 + 0.25, 0.25 + 0.5 * j / 2 + 0.25, 0.25 + 0.5 * k / 2 + 0.25]
                sh0 += [(c - 0.5) / c0 for c in col]
    gs = N("GaussianSplats", DEF="GS", positions=mf(pos, 3), scales=mf(scl, 3), orientations=mf(ori, 3), opacities=mf(opa, 2),
           sphericalHarmonicsDegree0Coef0=mf(sh0, 3), bboxSize="1.4 1.4 1.4", bboxCenter="0 0 0")
    kids = [N("Viewpoint", position="0 0 4", description="probe"), N("NavigationInfo", type='"NONE"', headlight=False), N("Background", skyColor="0 0 0"), gs]
    return document(kids, version=version, profile="Immersive" if version == "4.1" else "Immersive", components=[("GaussianSplats", 1)],
                    title="Loomsong probe splats %s" % version, description="27 splats on a lattice, bbox set", generator="loomsong gen/probes/make_probes.py")


def click_audio():
    sr, n = 48000, int(2.5 * 48000)
    y = np.zeros(n, dtype=np.float64)
    m = int(0.010 * sr)
    burst = 0.8 * np.sin(2 * math.pi * 2000 * np.arange(m) / sr) * np.hanning(m + 2)[1:-1]
    for t in (1.0, 2.0):
        i = int(round(t * sr))
        y[i:i + m] += burst
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    stereo = np.stack([pcm, pcm], axis=1)
    p = os.path.join(OUT, "click.wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(stereo.tobytes())
    enc = {"click.mp4": ["-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart"], "click.ogg": ["-c:a", "libopus", "-b:a", "192k"], "click.mp3": ["-c:a", "libmp3lame", "-b:a", "256k"]}
    for name, args in enc.items():
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", p, "-map_metadata", "-1", *args, os.path.join(OUT, name)], check=True)


PAGE = r"""<title>Loomsong probes</title>
<style>html,body{background:#000;margin:0}x3d-canvas{display:block;width:640px;height:360px}</style>
<script src="xite/x_ite.min.js"></script>
<x3d-canvas id="c" src="probe_a.x3d"></x3d-canvas>
<script>
const $ = id => document.getElementById(id);
const nextFrames = n => new Promise(res => { let i = 0; const f = () => (++i >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); });
window.probe = {
  B: () => X3D.getBrowser($('c')),
  async ready(name = 'FractionBus', timeout = 30000) {
    const t0 = performance.now();
    for (;;) {
      try { const s = this.B().currentScene; if (s && s.getNamedNode(name)) return true; } catch (e) {}
      if (performance.now() - t0 > timeout) throw new Error('scene did not load');
      await new Promise(r => setTimeout(r, 50));
    }
  },
  node(name) { return this.B().currentScene.getNamedNode(name); },
  frames: nextFrames,
  setFraction(f) { this.node('FractionBus').set_fraction = f; },
  state() {
    const sec = this.node('SecondsBus'), sh = this.node('Sh'), fb = this.node('FractionBus');
    return { fraction: fb.value_changed, seconds: sec.value_changed, u_time: sh.u_time, valid: sh.isValid };
  },
  async load(url, ready) { await this.B().loadURL(new X3D.MFString(url)); return this.ready(ready); },
  async decode(url) {
    const ctx = this.ctx || (this.ctx = new AudioContext());
    const t0 = performance.now();
    const buf = await (await fetch(url)).arrayBuffer();
    try {
      const ab = await ctx.decodeAudioData(buf.slice(0));
      const ch = ab.getChannelData(0), sr = ab.sampleRate;
      const first = ch.findIndex(v => Math.abs(v) > 0.05);
      let second = -1;
      for (let i = Math.floor(1.5 * sr); i < ch.length; i++) if (Math.abs(ch[i]) > 0.05) { second = i; break; }
      return { ok: true, bytes: buf.byteLength, duration: ab.duration, sampleRate: sr, channels: ab.numberOfChannels, onset1_s: first / sr, onset2_s: second / sr, ms: performance.now() - t0 };
    } catch (e) { return { ok: false, bytes: buf.byteLength, error: String(e) }; }
  },
  canPlay: () => { const a = document.createElement('audio'); return { mp4: a.canPlayType('audio/mp4; codecs="mp4a.40.2"'), ogg: a.canPlayType('audio/ogg; codecs="opus"'), mp3: a.canPlayType('audio/mpeg'), wav: a.canPlayType('audio/wav') }; },
  async clock(ms = 2000) {
    const ctx = this.ctx || (this.ctx = new AudioContext());
    await ctx.resume();
    const src = ctx.createBufferSource(); src.buffer = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate); src.connect(ctx.destination); src.start();
    const rows = [], t0 = performance.now();
    while (performance.now() - t0 < ms) {
      const ts = ctx.getOutputTimestamp();
      rows.push([performance.now(), ctx.currentTime, ts.contextTime, ts.performanceTime]);
      await new Promise(r => requestAnimationFrame(r));
    }
    return { state: ctx.state, outputLatency: ctx.outputLatency, baseLatency: ctx.baseLatency, sampleRate: ctx.sampleRate, rows };
  },
  version: () => ({ x_ite: X3D.getBrowser($('c')).version || null, ua: navigator.userAgent }),
};
</script>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, text in (("probe_a.x3d", probe_a()), ("probe_splat41.x3d", splat_scene("4.1")), ("probe_splat40_bad.x3d", splat_scene("4.0")), ("index.html", PAGE)):
        open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(text)
    open(os.path.join(OUT, "expect.json"), "w", newline="\n").write(json.dumps({"probe_splat40_bad.x3d": {"must_fail": ["fork-xsd", "version-fits-nodes"]}}, indent=1) + "\n")
    click_audio()
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
