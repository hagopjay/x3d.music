// The stage: a bare page that hosts one world in X_ITE, under the policy copy, with the time bus set by hand. Shared by stills, Behaviour and Eyes.
//   const s = await openStage(world, { W: 1280, H: 720 });   s.page, s.rec (console record), s.srv, s.L (browser), s.at(t, cam, fov, frames), s.close()
// The page owns the clock in the real page; here the stage plays its part: FractionBus.set_fraction = t / D, D read from the world's SecondsBus.
// Frame rates measured here are software-rendered and mean nothing (spec: Fps).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, launch, instrument, harmless } from './harness.mjs';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const pageHtml = (W, H) => `<title>Loomsong stage</title>
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
`;

export async function openStage(world, { W = 1280, H = 720, tag = null } = {}) {
  world = path.resolve(world);
  const site = path.join(ROOT, 'build', 'stage', tag || path.basename(world, '.x3d'));
  fs.rmSync(site, { recursive: true, force: true });
  fs.mkdirSync(site, { recursive: true });
  fs.copyFileSync(world, path.join(site, 'world.x3d'));
  fs.symlinkSync(path.join(ROOT, 'build', 'xite'), path.join(site, 'xite'));
  fs.writeFileSync(path.join(site, 'index.html'), pageHtml(W, H));
  const srv = await startServer({ root: site });
  const L = await launch();
  const page = await (await L.browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })).newPage();
  page.setDefaultTimeout(180000);
  const rec = await instrument(page, srv.base);
  const t0 = Date.now();
  await page.goto(srv.base, { waitUntil: 'load' });
  await page.evaluate(() => window.stage.ready());
  const info = await page.evaluate(() => window.stage.info());
  return {
    page, rec, srv, L, site, info, loadSeconds: (Date.now() - t0) / 1000,
    at: (t, cam = null, fov = null, frames = 6) => page.evaluate(([t, cam, fov, n]) => window.stage.at(t, cam, fov, n), [t, cam, fov, frames]),
    /** Console lines that count: errors, warnings, failed and refused requests, minus what the policy copy is known to refuse harmlessly. */
    problems() { return [...rec.errors, ...rec.console.filter(s => /^(error|warning)/.test(s)), ...rec.failed, ...rec.http].filter(s => !harmless(s) && !abortedAfterServed(s, srv.log)); },
    async close() { await rec.collectCsp().catch(() => {}); await L.browser.close(); await srv.close(); },
  };
}

/** Luminance facts of a PNG buffer, sampled on a 7-pixel stride: mean, median, 95th percentile and the share of near-black samples. */
export async function frameStats(page, png) {
  return page.evaluate(async b64 => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data; const lum = [];
    for (let i = 0; i < d.length; i += 4 * 7) lum.push((0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]) / 255);
    lum.sort((a, b) => a - b);
    return { mean: lum.reduce((s, v) => s + v, 0) / lum.length, p50: lum[Math.floor(lum.length * 0.5)], p95: lum[Math.floor(lum.length * 0.95)], black: lum.filter(v => v < 0.004).length / lum.length };
  }, png.toString('base64'));
}

/** Chrome reports a request X_ITE cancels after the body arrived as "<url> net::ERR_ABORTED" (the world file, once): not a refusal. It counts only if the server never answered 200 for that url (the server log is the witness). */
export const abortedAfterServed = (line, log) => {
  const m = /^(\S+) net::ERR_ABORTED$/.exec(line);
  return !!m && log.some(l => l.url === m[1] && l.status === 200);
};

export const shaderNames = world => [...fs.readFileSync(world, 'utf8').matchAll(/<ComposedShader[^>]*DEF='([^']+)'/g)].map(m => m[1]);
