#!/usr/bin/env node
// Render stills of a world at given score times, in headless Chrome under the policy copy, and write luminance facts beside them.
//   node witnesses/stills.mjs --world build/worlds/turca.x3d --times 12,60,150 [--out build/stills/turca] [--size 1280x720] [--cam "x y z  tx ty tz"] [--fov 60] [--name shot]
// The page is a bare stage: X_ITE as the page's own files, the world, and the time bus set by hand (FractionBus.set_fraction = t / D, D read from the world's SecondsBus).
// --cam overrides the directed camera after the time is set (a position and a look-at target); without it the stills show what the directed track does at that time.
// Output: <out>/<name>-<t>.png and <out>/stills.json {file, t, mean, p95, black, console}. Frame rates measured here are software-rendered and mean nothing (spec: Fps).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, launch, instrument, harmless, samplePixels, sleep } from './harness.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const arg = (k, d = null) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const world = path.resolve(arg('world'));
const times = arg('times', '0').split(',').map(Number);
const out = path.resolve(arg('out', path.join(ROOT, 'build', 'stills', path.basename(world, '.x3d'))));
const [W, H] = arg('size', '1280x720').split('x').map(Number);
const cam = arg('cam') ? arg('cam').trim().split(/\s+/).map(Number) : null;
const fov = arg('fov') ? Number(arg('fov')) * Math.PI / 180 : null;
const name = arg('name', path.basename(world, '.x3d'));
const settle = Number(arg('frames', '6'));

const site = path.join(ROOT, 'build', 'stage', path.basename(world, '.x3d'));
fs.rmSync(site, { recursive: true, force: true });
fs.mkdirSync(site, { recursive: true });
fs.copyFileSync(world, path.join(site, 'world.x3d'));
fs.symlinkSync(path.join(ROOT, 'build', 'xite'), path.join(site, 'xite'));
fs.writeFileSync(path.join(site, 'index.html'), `<title>Loomsong stage</title>
<style>html,body{background:#000;margin:0}x3d-canvas{display:block;width:${W}px;height:${H}px}</style>
<script src="xite/x_ite.min.js"></script>
<x3d-canvas id="c" src="world.x3d"></x3d-canvas>
<script>
const B = () => X3D.getBrowser(document.getElementById('c'));
const frames = n => new Promise(res => { let i = 0; const f = () => (++i >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); });
window.stage = {
  async ready(timeout = 120000) {
    const t0 = performance.now();
    for (;;) {
      try { const s = B().currentScene; if (s && s.getNamedNode('FractionBus')) return true; } catch (e) {}
      if (performance.now() - t0 > timeout) throw new Error('scene did not load');
      await new Promise(r => setTimeout(r, 100));
    }
  },
  node: n => B().currentScene.getNamedNode(n),
  frames,
  duration() { const k = this.node('SecondsBus').keyValue; return k[k.length - 1]; },
  async at(t, cam, fov, n) {
    this.node('FractionBus').set_fraction = t / this.duration();
    await frames(2);
    if (cam) {
      const v = this.node('Cam');
      if (v) {
        const e = cam.slice(0, 3), g = cam.slice(3, 6);
        v.position = new X3D.SFVec3f(...e);
        v.orientation = lookRot(e, g);
        if (fov) v.fieldOfView = fov;
      }
    }
    await frames(n);
  },
  shaders(names) { const sc = B().currentScene; return names.map(nm => { try { const nd = sc.getNamedNode(nm); return { name: nm, valid: nd.isValid }; } catch (e) { return { name: nm, valid: null }; } }); },
  info() { const g = B().getContext(); return { renderer: g.getParameter(g.RENDERER), size: [g.drawingBufferWidth, g.drawingBufferHeight] }; },
};
function lookRot(e, g) {
  const f = [g[0] - e[0], g[1] - e[1], g[2] - e[2]]; const n = Math.hypot(...f); f.forEach((_, i) => f[i] /= n);
  let r = [f[1] * 0 - f[2] * 1, f[2] * 0 - f[0] * 0, f[0] * 1 - f[1] * 0]; // f x up(0,1,0)
  r = [-f[2], 0, f[0]]; const rn = Math.hypot(...r) || 1; r = r.map(v => v / rn);
  const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
  const m = [[r[0], u[0], -f[0]], [r[1], u[1], -f[1]], [r[2], u[2], -f[2]]];
  const tr = m[0][0] + m[1][1] + m[2][2]; const a = Math.acos(Math.max(-1, Math.min(1, (tr - 1) / 2)));
  if (a < 1e-9) return new X3D.SFRotation(0, 1, 0, 0);
  const ax = [m[2][1] - m[1][2], m[0][2] - m[2][0], m[1][0] - m[0][1]]; const an = Math.hypot(...ax) || 1;
  return new X3D.SFRotation(ax[0] / an, ax[1] / an, ax[2] / an, a);
}
</script>
`);

fs.mkdirSync(out, { recursive: true });
const srv = await startServer({ root: site });
const L = await launch();
const page = await (await L.browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })).newPage();
page.setDefaultTimeout(180000);
const rec = await instrument(page, srv.base);
const rows = [];
try {
  const t0 = Date.now();
  await page.goto(srv.base, { waitUntil: 'load' });
  await page.evaluate(() => window.stage.ready());
  console.log('loaded in', ((Date.now() - t0) / 1000).toFixed(1), 's', JSON.stringify(await page.evaluate(() => window.stage.info())));
  const names = [...fs.readFileSync(world, 'utf8').matchAll(/<ComposedShader[^>]*DEF='([^']+)'/g)].map(m => m[1]);
  const sv = await page.evaluate(n => window.stage.shaders(n), names);
  const bad = sv.filter(x => x.valid !== true);
  console.log(`shaders ${sv.length}, valid ${sv.length - bad.length}${bad.length ? ', NOT VALID: ' + bad.map(x => x.name).join(' ') : ''}`);
  for (const t of times) {
    const t1 = Date.now();
    await page.evaluate(([t, cam, fov, n]) => window.stage.at(t, cam, fov, n), [t, cam, fov, settle]);
    const png = await page.screenshot({ type: 'png' });
    const file = path.join(out, `${name}-${String(t).replace('.', '_')}.png`);
    fs.writeFileSync(file, png);
    const stats = await page.evaluate(async b64 => {
      const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
      const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
      const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data; const lum = [];
      for (let i = 0; i < d.length; i += 4 * 7) lum.push((0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]) / 255);
      lum.sort((a, b) => a - b);
      return { mean: lum.reduce((s, v) => s + v, 0) / lum.length, p95: lum[Math.floor(lum.length * 0.95)], p50: lum[Math.floor(lum.length * 0.5)], black: lum.filter(v => v < 0.004).length / lum.length };
    }, png.toString('base64'));
    rows.push({ file: path.relative(ROOT, file), t, ...stats });
    console.log(`t=${t}  mean ${stats.mean.toFixed(3)}  median ${stats.p50.toFixed(3)}  p95 ${stats.p95.toFixed(3)}  black ${(stats.black * 100).toFixed(0)}%  ${((Date.now() - t1) / 1000).toFixed(1)} s  ${path.relative(ROOT, file)}`);
  }
} finally {
  await rec.collectCsp().catch(() => {});
  const bad = [...rec.errors, ...rec.console.filter(s => /^(error|warning)/.test(s)), ...rec.failed, ...rec.http].filter(s => !harmless(s));
  fs.writeFileSync(path.join(out, 'stills.json'), JSON.stringify({ world: path.relative(ROOT, world), size: [W, H], rows, console: bad, csp: rec.csp }, null, 1));
  if (bad.length) console.log('CONSOLE', bad.slice(0, 12).join('\n  '));
  await L.browser.close();
  await srv.close();
}
