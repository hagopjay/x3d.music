#!/usr/bin/env node
// Host witness (spec): both worlds play start to end under the strict policy copy, with 0 blocked requests.
//   node witnesses/host.mjs [--steps 110] [--runs build/runs]
// What "play start to end" means here, measured:
//   1. Stepped: with the test clock (?clock=manual) every piece is walked from 0 to its end in `steps` settings of the clock; at each one the page sets the bus and two frames are drawn. The page
//      must stay up, the scene must follow the bus, nothing may be refused, the end card must come up at the end.
//   2. Real clock: the page is opened without the test clock, Play is pressed, and for a few seconds the real audio clock (Web Audio, decoded from the .mp4) must run and the bus must follow it.
// "Blocked" is any request the server refused or the browser cut before an answer, any Content-Security-Policy violation that is not one of the known harmless ones (X_ITE's own interface font and its
// tangent generator's WebAssembly, neither of which the page uses), and any file asked for that is not in the published set. A request X_ITE cancels after the server already answered 200 is not blocked.
// The policy is a copy written from the Artifact page contract: a pass is C under the copy and L on the real host.
import fs from 'node:fs';
import path from 'node:path';
import { openPage } from './pagekit.mjs';
import { ROOT } from './stage.mjs';
import { harmless } from './harness.mjs';

const argv = process.argv.slice(2);
const arg = (k, d = null) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const steps = Number(arg('steps', '110'));
const runs = path.resolve(arg('runs', path.join(ROOT, 'build', 'runs')));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(30) + detail); };
const record = { witness: 'host', policy: 'strict copy (scripts self + inline + five CDNs, fetch self, no unsafe-eval, no wasm compile)' };

// ---- 1. stepped, both pieces
const A = await openPage({ manual: true });
try {
  const pieces = await A.page.evaluate(() => Loomsong.pieces.map(p => ({ id: p.id, D: p.D })));
  record.stepped = [];
  for (const p of pieces) {
    if (await A.page.evaluate(() => Loomsong.piece.id) !== p.id) await A.page.evaluate(id => Loomsong.openPiece(id, false), p.id);
    await A.page.evaluate(() => document.querySelector('.ls-big').click());
    await A.frames(2);
    let worst = 0, seen = 0, ended = false;
    const t0 = Date.now();
    for (let i = 0; i <= steps; i++) {
      const t = p.D * i / steps;
      const r = await A.page.evaluate(async t => {
        const L = Loomsong; L.clock.setTime(t);
        await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
        return { f: L.nodes.bus.fraction_changed !== undefined ? null : null, sent: L.lastSent, sec: L.nodes.sec.value_changed, t: L.t };
      }, t);
      worst = Math.max(worst, Math.abs(r.sec - t));
      seen++;
    }
    ended = await A.page.evaluate(async D => { Loomsong.clock.setTime(D); await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res))); return Loomsong.clock.ended || document.querySelector('.ls-credits').getAttribute('data-show') === '1'; }, p.D);
    const sec = ((Date.now() - t0) / 1000).toFixed(0);
    check(`stepped ${p.id}`, worst < 0.02 && seen === steps + 1, `${seen} settings across ${p.D.toFixed(1)} s in ${sec} s; the scene's clock followed the page's to ${worst.toExponential(1)} s`);
    check(`end card ${p.id}`, ended, ended ? 'the end card came up at the end' : 'no end card at the end');
    record.stepped.push({ piece: p.id, settings: seen, worst, ended });
  }
  const prob = A.problems();
  const csp = (await A.rec.collectCsp()).filter(x => !harmless(x));
  const served = A.srv.log;
  const missing = served.filter(l => l.status !== 200 && !/favicon/.test(l.url));
  check('stepped: nothing refused', prob.length === 0 && csp.length === 0 && missing.length === 0, prob.length || csp.length || missing.length ? [...prob, ...csp, ...missing.map(l => l.url + ' ' + l.status)].slice(0, 6).join(' | ') : `${served.length} requests, all answered 200; 0 policy violations beyond the known harmless ones; 0 console errors or warnings`);
  record.stepped_requests = served.length;
  record.console_lines = A.rec.console.length;
  const errs = (await A.page.evaluate(() => Loomsong.errors)).filter(e => !harmless(e));
  check('stepped: page errors', errs.length === 0, errs.length ? errs.slice(0, 4).join(' | ') : 'none');
} finally { await A.close(); }

// ---- 2. real clock
const B = await openPage({ manual: false });
try {
  const mode = await B.page.evaluate(() => Loomsong.clock.mode);
  check('real clock: decoded', mode === 'webaudio', `the master decoded through Web Audio (mode ${mode}); ${JSON.stringify(await B.page.evaluate(() => Loomsong.clock.info()))}`);
  await B.page.evaluate(() => document.querySelector('.ls-big').click());
  await B.frames(10);
  const a = await B.page.evaluate(() => ({ t: Loomsong.clock.now(), perf: performance.now() }));
  await new Promise(r => setTimeout(r, 5000));
  await B.frames(5);
  const b = await B.page.evaluate(() => ({ t: Loomsong.clock.now(), perf: performance.now(), sent: Loomsong.lastSent, frameMs: Loomsong.frameMs, playing: Loomsong.clock.playing, state: Loomsong.clock.ctx.state, sec: Loomsong.nodes.sec.value_changed }));
  const dt = (b.perf - a.perf) / 1000, dc = b.t - a.t;
  check('real clock: runs', b.playing && b.state === 'running' && Math.abs(dc - dt) < 0.25, `the audio clock advanced ${dc.toFixed(3)} s while the page's clock advanced ${dt.toFixed(3)} s; context ${b.state}`);
  const gap = Math.abs(b.sec - b.sent), frame = b.frameMs / 1000;
  check('real clock: bus follows', gap <= 2 * frame + 0.01, `the scene's clock ${b.sec.toFixed(3)} s against the last time the page sent ${b.sent.toFixed(3)} s: ${(gap * 1000).toFixed(0)} ms apart, a frame here is ${(frame * 1000).toFixed(0)} ms (software drawing; one frame of lag is by design)`);
  const prob = B.problems();
  const csp = (await B.rec.collectCsp()).filter(x => !harmless(x));
  check('real clock: nothing refused', prob.length === 0 && csp.length === 0, prob.length || csp.length ? [...prob, ...csp].slice(0, 6).join(' | ') : `${B.srv.log.length} requests, 0 refused`);
  record.real = { dc, dt, state: b.state };
} finally { await B.close(); }

const ok = checks.every(c => c.ok);
fs.writeFileSync(path.join(runs, 'host.json'), JSON.stringify({ ...record, ok, checks }, null, 1));
console.log(ok ? 'Host green (under the policy copy)' : 'Host RED');
process.exitCode = ok ? 0 : 1;
