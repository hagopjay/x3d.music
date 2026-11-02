#!/usr/bin/env node
// P0 probes: run the probe scenes and audio files from build/probes under the policy copy in headless Chrome and write graded facts.
//   node witnesses/probes.mjs [--out build/runs/p0/probes.json] [--strict]
// Probe A  time bus + per-vertex attributes + an event data texture (nearest, 16-bit time in two 8-bit channels): is each strip lit when it should be?
// Probe C  audio: decode of AAC in mp4, Opus in ogg, mp3 and wav; onset error of two bursts; the AudioContext clock against performance.now().
// Probe D  4.1 GaussianSplats: does the pinned X_ITE draw them, and what does it do with the same node declared as 4.0?
// Each check is {id, claim, observed, ok}; the grade (C/L/S) is written in docs/PROBES.md beside the line, because it depends on where the check ran.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, launch, instrument, harmless, samplePixels, sleep, CSP, CSP_WASM } from './harness.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.join(ROOT, 'build', 'probes');
const argv = process.argv.slice(2);
const OUT = argv.includes('--out') ? path.resolve(argv[argv.indexOf('--out') + 1]) : path.join(ROOT, 'build', 'runs', 'p0', 'probes.json');
const STRICT = argv.includes('--strict');
const D = 230, STRIPS = 8, f32 = Math.fround;

const checks = [];
const check = (id, claim, observed, ok) => { checks.push({ id, claim, observed, ok: !!ok }); console.log((ok ? 'PASS ' : 'FAIL ') + id + '  ' + claim + '  [' + (typeof observed === 'string' ? observed : JSON.stringify(observed)) + ']'); };
const fit = (xs, ys) => {                                                  // least squares y = a + b x; returns slope, intercept, max |residual|
  const n = xs.length, mx = xs.reduce((s, v) => s + v, 0) / n, my = ys.reduce((s, v) => s + v, 0) / n;
  let sxx = 0, sxy = 0; for (let i = 0; i < n; i++) { sxx += (xs[i] - mx) ** 2; sxy += (xs[i] - mx) * (ys[i] - my); }
  const b = sxy / sxx, a = my - b * mx; let r = 0; for (let i = 0; i < n; i++) r = Math.max(r, Math.abs(ys[i] - (a + b * xs[i])));
  return { slope: b, intercept: a, maxResidual: r };
};

fs.mkdirSync(path.dirname(OUT), { recursive: true });
const link = path.join(SITE, 'xite');
if (!fs.existsSync(link)) fs.symlinkSync(path.join('..', 'xite'), link);

const srv = await startServer({ root: SITE });
const L = await launch();
const R = { schema: 'loomsong.probes/1', browser: { chrome: L.chrome, playwright: L.playwright, gl: L.gl }, probes: {}, checks };
const page = await (await L.browser.newContext({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 })).newPage();
page.setDefaultTimeout(90000);
const rec = await instrument(page, srv.base);
const shot = async name => { const b = await page.screenshot({ type: 'png' }); fs.writeFileSync(path.join(path.dirname(OUT), name + '.png'), b); return b; };

try {
  await page.goto(srv.base, { waitUntil: 'load' });
  await page.evaluate(() => window.probe.ready());
  R.environment = await page.evaluate(() => {
    const B = window.probe.B(), gl = B.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info');
    return { xite: B.version || (B.getVersion && B.getVersion()) || null, webgl: gl.getParameter(gl.VERSION), glsl: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
             renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null, maxTexture: gl.getParameter(gl.MAX_TEXTURE_SIZE), maxVertexAttribs: gl.getParameter(gl.MAX_VERTEX_ATTRIBS), ua: navigator.userAgent };
  });
  console.log('environment', JSON.stringify(R.environment));

  // ---------------------------------------------------------------- Probe A
  const A = { shots: [] };
  const st0 = await page.evaluate(() => window.probe.state());
  check('A0', 'the shader program links (ComposedShader.isValid) with data: ShaderParts, in/out GLSL ES 3.00, flat varying, texelFetch and per-vertex attributes', st0, st0.valid === true);
  const tOn = k => k * D / STRIPS, q16 = k => Math.round(tOn(k) / D * 65535), texT = k => q16(k) / 65535 * D;
  const centre = k => [Math.round(57.5 + 75 * k), 180];
  const expectAttr = (u, k) => f32(tOn(k)) <= u;
  const expectTex = (u, k) => f32(f32(texT(k)) - 0.004) <= u;
  const times = [0, 0.3 * D, 0.6 * D, D];                                      // whole-scene fractions, then both sides of every threshold by 1 ms
  for (let k = 1; k < STRIPS; k++) for (const t of [tOn(k) - 0.001, tOn(k) + 0.001, texT(k) - 0.004 - 0.001, texT(k) - 0.004 + 0.001]) times.push(t);
  let mism = 0, mismTex = 0, maxU = 0, nearBad = 0, total = 0, firstBad = null;
  for (const t of times) {
    const f = t / D;
    await page.evaluate(f => window.probe.setFraction(f), f);
    await page.evaluate(() => window.probe.frames(4));
    const st = await page.evaluate(() => window.probe.state());
    const png = await page.screenshot({ type: 'png' });
    const pts = []; for (let k = 0; k < STRIPS; k++) { const [x, y] = centre(k); pts.push([x, y], [x - 18, y - 40], [x + 18, y + 40]); }
    const px = await samplePixels(page, png, pts);
    const u = st.u_time; maxU = Math.max(maxU, Math.abs(u - t));
    for (let k = 0; k < STRIPS; k++) {
      for (let j = 0; j < 3; j++) {
        const p = px[3 * k + j], ea = expectAttr(u, k), et = expectTex(u, k);
        const la = p[0] > 127, lt = p[1] > 127, near = p[2] < 6 || p[2] > 249, par = p[2] > 127;
        total++;
        if (la !== ea) { mism++; firstBad = firstBad || { t, k, j, kind: 'attr', got: la, want: ea, px: p }; }
        if (lt !== et) { mismTex++; firstBad = firstBad || { t, k, j, kind: 'texture', got: lt, want: et, px: p }; }
        if (!near || par !== (k % 2 === 1)) nearBad++;
      }
    }
    if (A.shots.length < 4) { await shot('probe_a_f' + f.toFixed(2)); }
    A.shots.push({ t: +t.toFixed(4), u_time: u, px0: px[0].slice(0, 3), pxLast: px[3 * (STRIPS - 1)].slice(0, 3) });
  }
  A.tested = { fractions: times.length, pixels: total, maxTimeError_s: maxU };
  check('A1', 'u_time in the shader equals fraction x 230 s through FractionBus -> SecondsBus (max error over ' + times.length + ' settings)', { maxTimeError_s: maxU }, maxU < 1e-4);
  check('A2', 'a strip lights from its per-vertex onset attribute within 1 ms of the exact time (' + total + ' pixel checks)', { mismatches: mism, first: firstBad && firstBad.kind === 'attr' ? firstBad : null }, mism === 0);
  check('A3', 'a strip lights from the event texture (16-bit time in R and G) within the 4 ms slack, both sides of every threshold', { mismatches: mismTex, first: firstBad && firstBad.kind === 'texture' ? firstBad : null }, mismTex === 0);
  check('A4', 'the data texture is read with NEAREST filtering and unchanged colour (B channel exactly 0 or 255, 0.45 texel off centre)', { badPixels: nearBad }, nearBad === 0);
  R.probes.A = A;

  // ---------------------------------------------------------------- Probe C
  const C = { canPlay: await page.evaluate(() => window.probe.canPlay()), decode: {} };
  for (const f of ['wav', 'mp4', 'ogg', 'mp3']) C.decode[f] = await page.evaluate(u => window.probe.decode(u), 'click.' + f);
  const base1 = C.decode.wav.ok ? C.decode.wav.onset1_s : 1.0, base2 = C.decode.wav.ok ? C.decode.wav.onset2_s : 2.0;
  for (const f of ['mp4', 'ogg', 'mp3']) {
    const d = C.decode[f];
    if (d.ok) { d.onsetShift1_ms = +((d.onset1_s - base1) * 1000).toFixed(3); d.onsetShift2_ms = +((d.onset2_s - base2) * 1000).toFixed(3); }
  }
  check('C1', 'wav decodes and the two bursts sit at 1.000 s and 2.000 s (reference for the others)', C.decode.wav, C.decode.wav.ok && Math.abs(base1 - 1) < 0.003 && Math.abs(base2 - 2) < 0.003);
  for (const f of ['mp4', 'ogg', 'mp3']) {
    const d = C.decode[f];
    check('C-' + f, f + ' decodes in decodeAudioData and keeps the burst times within 5 ms of the wav', d.ok ? { duration: d.duration, sampleRate: d.sampleRate, shift1_ms: d.onsetShift1_ms, shift2_ms: d.onsetShift2_ms, bytes: d.bytes } : d,
          d.ok && Math.abs(d.onsetShift1_ms) < 5 && Math.abs(d.onsetShift2_ms) < 5);
  }
  // 8 s, not 2.5 s (2 Nov 2026): the context clock moves in audio-callback steps, and on a shared runner one stall of 3 ms at either end of a short window moves the fitted slope by 0.0013, which is more
  // than the tolerance below (a CI run read 0.998667 over 2.5 s while the page-facing check, C6, read 1.000000 in the same run). The same stall over 8 s moves it by 0.0004. The tolerance did not change.
  const clk = await page.evaluate(() => window.probe.clock(8000));
  const t = clk.rows.map(r => r[0] / 1000), cur = clk.rows.map(r => r[1]), ctxT = clk.rows.map(r => r[2]), perfT = clk.rows.map(r => r[3] / 1000);
  const moved = cur[cur.length - 1] - cur[0];
  const fitCur = fit(t, cur), fitTs = fit(perfT, ctxT);
  const offs = clk.rows.map(r => r[0] - r[3]);
  C.clock = { state: clk.state, sampleRate: clk.sampleRate, baseLatency_ms: clk.baseLatency * 1000, outputLatency_ms: clk.outputLatency * 1000, frames: clk.rows.length, contextAdvanced_s: moved,
              slope_vs_performance: fitCur.slope, maxResidual_ms: fitCur.maxResidual * 1000, timestampSlope: fitTs.slope, timestampMaxResidual_ms: fitTs.maxResidual * 1000,
              performanceMinusTimestamp_ms: { min: Math.min(...offs), max: Math.max(...offs) },
              rows: clk.rows.map(r => r.map(v => +v.toFixed(3))) };   // kept so that a red C5 can be read afterwards: [performance.now, currentTime, timestamp context time, timestamp performance time]
  check('C5', 'the AudioContext runs and its clock advances at 1.000 +/- 0.001 of performance.now() over 8 s', { state: clk.state, advanced_s: +moved.toFixed(4), slope: +fitCur.slope.toFixed(6), outputLatency_ms: C.clock.outputLatency_ms },
        clk.state === 'running' && Math.abs(fitCur.slope - 1) < 0.001);
  check('C6', 'getOutputTimestamp() maps context time to performance time with slope 1 +/- 0.001', { slope: +fitTs.slope.toFixed(6), maxResidual_ms: +C.clock.timestampMaxResidual_ms.toFixed(3) }, Math.abs(fitTs.slope - 1) < 0.001);
  R.probes.C = C;

  // ---------------------------------------------------------------- Probe D
  // One fresh page per (policy, file): a splat load that never finishes must not take the other probes with it.
  const splatRun = async (variant, csp, file) => {
    const s = await startServer({ root: SITE, csp });
    const pg = await (await L.browser.newContext({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 })).newPage();
    const r2 = await instrument(pg, s.base);
    const out = { policy: variant, file };
    try {
      await pg.goto(s.base, { waitUntil: 'load' });
      await pg.evaluate(() => window.probe.ready());
      out.load = await Promise.race([
        pg.evaluate(([u, n]) => window.probe.load(u, n).then(() => 'loaded'), [file, 'GS']).catch(e => 'error: ' + String(e).slice(0, 200)),
        sleep(25000).then(() => 'did not finish in 25 s')]);
      await pg.evaluate(() => window.probe.frames(8)).catch(() => {});
      await sleep(600);
      out.node = await pg.evaluate(() => {
        try { const s = window.probe.B().currentScene, n = s.getNamedNode('GS'); return { type: n.getNodeTypeName(), version: s.specificationVersion, profile: s.profile && s.profile.name }; }
        catch (e) { return { error: String(e).slice(0, 160) }; }
      });
      const png = await pg.screenshot({ type: 'png' });
      fs.writeFileSync(path.join(path.dirname(OUT), 'splat_' + variant + '_' + file.replace(/\.x3d$/, '') + '.png'), png);
      const pts = []; for (let y = 10; y < 360; y += 20) for (let x = 10; x < 640; x += 20) pts.push([x, y]);
      const px = await samplePixels(pg, png, pts);
      const lit = px.filter(p => p[0] + p[1] + p[2] > 40);
      out.grid = { points: px.length, nonBlack: lit.length, distinctColours: new Set(lit.map(p => p.slice(0, 3).map(v => v >> 4).join(','))).size };
      out.notices = r2.console.filter(m => /Sort worker|WebAssembly|CompileError|GaussianSplats|Unknown|not supported|Warning/i.test(m)).map(m => m.slice(0, 220)).slice(0, 4);
      out.draws = out.load === 'loaded' && out.grid.nonBlack > 12 && out.grid.distinctColours >= 3;
    } catch (e) { out.error = String(e).slice(0, 300); out.draws = false; }
    await pg.context().close(); await s.close();
    return out;
  };
  const SP = { strict41: await splatRun('strict', CSP, 'probe_splat41.x3d'), wasm41: await splatRun('wasm', CSP_WASM, 'probe_splat41.x3d'), wasm40: await splatRun('wasm', CSP_WASM, 'probe_splat40_bad.x3d') };
  check('D1', "with 'wasm-unsafe-eval' allowed, the pinned X_ITE instantiates GaussianSplats from an X3D 4.1 file (bboxSize, bboxCenter set) and draws it (>12 of 576 grid points lit, >=3 colours)", { node: SP.wasm41.node, grid: SP.wasm41.grid, load: SP.wasm41.load }, SP.wasm41.draws && SP.wasm41.node && SP.wasm41.node.type === 'GaussianSplats');
  check('D2', "under the strict policy copy (no 'wasm-unsafe-eval') the splat sorter's WebAssembly is refused and the splats do not draw (recorded fact; flips if the policy or X_ITE changes)", { load: SP.strict41.load, draws: SP.strict41.draws, notices: SP.strict41.notices }, !SP.strict41.draws && SP.strict41.notices.some(m => /WebAssembly|CompileError|Sort worker/i.test(m)));
  check('D3', 'the same node in a file declared X3D 4.0, policy with wasm allowed: what the browser does (recorded, not graded)', { node: SP.wasm40.node, load: SP.wasm40.load, draws: SP.wasm40.draws, grid: SP.wasm40.grid, notices: SP.wasm40.notices }, true);
  R.probes.D = SP;

  await rec.collectCsp();
  R.page = { csp: rec.csp.filter(m => !harmless(m)), cspHarmless: rec.csp.filter(harmless), errors: rec.errors.filter(m => !harmless(m)), failed: rec.failed.filter(m => !harmless(m)), http: rec.http.filter(m => !harmless(m)), console: rec.console.filter(m => !harmless(m)).slice(0, 40), served: srv.log.length };
  check('H1', 'no CSP violation, page error or failed request under the policy copy during the whole run (known-harmless font and wasm notices excluded)', { csp: R.page.csp.length, harmlessCsp: R.page.cspHarmless, errors: R.page.errors.length, failed: R.page.failed.length, http: R.page.http.length },
        R.page.csp.length === 0 && R.page.errors.length === 0 && R.page.failed.length === 0 && R.page.http.length === 0);
} catch (e) {
  check('RUN', 'the probe run completes', String(e && e.stack || e).slice(0, 600), false);
} finally {
  R.summary = { passed: checks.filter(c => c.ok).length, failed: checks.filter(c => !c.ok).length };
  // the record is committed: no random port numbers, and no vendor word from the GL renderer string
  const text = JSON.stringify(R, null, 1).replace(/127\.0\.0\.1:\d+/g, '127.0.0.1:PORT').replace(/ANGLE \(\w+, /, 'ANGLE (');
  fs.writeFileSync(OUT, text + '\n');
  await L.browser.close(); await srv.close();
  console.log('wrote', path.relative(ROOT, OUT), JSON.stringify(R.summary));
}
process.exit(STRICT && R.summary.failed ? 1 : 0);
