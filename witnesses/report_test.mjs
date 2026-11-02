#!/usr/bin/env node
// Report tests: the page's diagnostics reporter does what it says where the host gives the page a store, and nothing at all where it does not.
//   node witnesses/report_test.mjs [--runs build/runs]
// Checks: with no store (every other witness, a plain server) the report is off: no probe, no write, no word on the splash. The frame-time statistics, a fixed histogram, give a made-up series its
// median and 1 % low to a quarter millisecond. Play, pause and end are noticed (the driver does not announce its own play and pause), frames are timed only while playing, a gap that was not a frame is
// dropped, writes go one at a time however often they are asked for, and a refused write is caught, remembered and waited out. With a stand-in for the host's store the real page writes one small
// document, reports/<id>: the browser, the graphics renderer, what the policy allows, how long each world took, how the clock was set up, the play and pause it saw; switching pieces adds the second.
import fs from 'node:fs';
import path from 'node:path';
import { openPage } from './pagekit.mjs';
import { ROOT } from './stage.mjs';

const runs = path.resolve(process.argv.includes('--runs') ? process.argv[process.argv.indexOf('--runs') + 1] : path.join(ROOT, 'build', 'runs'));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(34) + detail); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// The host's store, as far as the report can tell: db.doc(path).set(data), slow enough that two overlapping writes would show.
const standIn = () => {
  const S = window.__db = { store: {}, writes: 0, inflight: 0, maxInflight: 0, maxBytes: 0, paths: [] };
  window.loomHost = { use: async name => name !== 'db' ? null : { doc: path => ({ set: async data => {
    S.inflight++; S.maxInflight = Math.max(S.maxInflight, S.inflight);
    await new Promise(r => setTimeout(r, 120));
    const s = JSON.stringify(data); S.maxBytes = Math.max(S.maxBytes, s.length); S.store[path] = JSON.parse(s); S.writes++; S.paths.push(path); S.inflight--;
  } }) } };
};

let N, B;
try {
  // ------------------------------------------------------------------ no store: the report is off
  N = await openPage({ manual: true });
  const off = await N.page.evaluate(async () => ({ on: await Loomsong.report.ready, db: Loomsong.report.db, writes: Loomsong.report.writes, env: !!Loomsong.report.doc.env, policy: !!Loomsong.report.doc.policy, small: document.querySelector('.ls-small').textContent }));
  check('off where there is no store', off.on === false && off.db === null && off.writes === 0 && !off.env && !off.policy && !/builder/.test(off.small), `ready ${off.on}, writes ${off.writes}, nothing probed, the splash says nothing of it`);

  // ------------------------------------------------------------------ statistics and the frame logic, with a stub app so every number is exact
  const st = await N.page.evaluate(() => {
    const S = LoomReport.FrameStats, a = new S(), b = new S();
    for (let i = 0; i < 980; i++) a.add(16.667);
    for (let i = 0; i < 20; i++) a.add(51);
    for (let i = 0; i < 1000; i++) b.add(16.667);
    return { a: a.summary(), b: b.summary() };
  });
  const want = { frames: 1000, seconds: 17.4, medianFps: 59.7, low1Fps: 19.5, over33ms: 20, over50ms: 20, maxMs: 51 };
  check('statistics: 2 % slow frames', Object.keys(want).every(k => st.a[k] === want[k]), `980 frames of 16.667 ms and 20 of 51 ms give ${JSON.stringify(st.a)}`);
  check('statistics: a steady series', st.b.medianFps === 59.7 && st.b.low1Fps === 59.7 && st.b.over33ms === 0, `1000 frames of 16.667 ms give median ${st.b.medianFps} and 1 % low ${st.b.low1Fps} (the upper edge of a quarter-millisecond bucket, so never flattering)`);

  const stub = await N.page.evaluate(async () => {
    const h = {}, app = { on: (k, f) => { h[k] = f; }, clock: { playing: false, ended: false, info: () => ({ mode: 'stub', lastError: new Error('late') }) }, piece: { id: 'x' }, errors: ['boom'] };
    const writes = [], S = { inflight: 0, max: 0 };
    const db = { doc: p => ({ set: async d => { S.inflight++; S.max = Math.max(S.max, S.inflight); await new Promise(r => setTimeout(r, 60)); writes.push([p, JSON.parse(JSON.stringify(d))]); S.inflight--; } }) };
    const rep = new LoomReport(app, () => db);
    await rep.ready;
    h.loading({ id: 'x' }); h.piece({ id: 'x' }, {});
    let perf = 1000;
    for (let i = 0; i < 5; i++) h.frame(0, perf += 16.7);                      // not playing: not timed
    app.clock.playing = true;
    for (let i = 0; i < 50; i++) h.frame(0, perf += 16.7);                     // the first of these notes the play and has no earlier frame to time from
    h.frame(0, perf += 2500);                                                  // a stall that was not a frame
    for (let i = 0; i < 10; i++) h.frame(0, perf += 16.7);
    app.clock.playing = false; h.frame(0, perf += 16.7);                      // pause
    app.clock.ended = true; h.frame(0, perf += 16.7);                         // end
    const snap = rep.snapshot(), logNow = snap.log.map(l => l[1]);               // a copy: the page's listeners are shared, so a second report made below would log into this one's list too
    // ten writes asked for at once
    rep.holdUntil = 0;
    for (let i = 0; i < 10; i++) rep.flush();
    await new Promise(r => setTimeout(r, 3500));
    // a refused write
    const bad = new LoomReport(app, () => ({ doc: () => ({ set: () => Promise.reject({ code: 'rate_limited' }) }) }));
    await bad.ready;
    let threw = false, res = null;
    try { res = await bad.flush(); } catch (e) { threw = true; }
    return { log: logNow, play: snap.play, errors: snap.errors, piece: snap.pieces.x, max: S.max, writes: writes.length, lastLog: writes.length ? writes[writes.length - 1][1].log.length : 0, threw, res, writeError: bad.doc.writeError, held: bad.holdUntil - performance.now() };
  });
  // the strict policy copy refuses the WebAssembly probe, and the refusal is logged too; a host that allows it logs none, so the refusals are left out of the comparison
  check('play, pause and end are noticed', stub.log.filter(s => !/^policy refused/.test(s)).join('|') === 'policy probed|asked for x|x ready|play x|pause x|ended x', stub.log.join(' | '));
  check('frames are timed only while playing', stub.play.x && stub.play.x.frames === 59 && stub.play.x.over50ms === 0, `5 frames before Play, 50 after it (49 timed: the first had no earlier frame), a 2.5 s stall dropped, 10 more: ${stub.play.x ? stub.play.x.frames : 'none'} timed`);
  check('an Error in the clock info is text', stub.piece && stub.piece.clock && stub.piece.clock.lastError === 'Error: late' && stub.errors[0] === 'boom', `lastError ${JSON.stringify(stub.piece && stub.piece.clock && stub.piece.clock.lastError)}`);
  check('writes go one at a time', stub.max === 1 && stub.writes >= 2 && stub.writes <= 5, `ten flushes at once, ${stub.writes} writes in all, at most ${stub.max} in flight`);
  check('a refused write is caught', !stub.threw && stub.res === false && stub.writeError === 'rate_limited' && stub.held > 25000, `flush gave ${stub.res}, writeError ${stub.writeError}, waits ${Math.round(stub.held / 1000)} s before the next try`);
  await N.close(); N = null;

  // a host name in the address whose object never comes: two seconds of looking, then off; and the address has no say outside the test clock
  const Z = await openPage({ manual: true, query: 'hostapi=nobody' });
  try {
    const t0 = Date.now();
    const z = await Z.page.evaluate(async () => ({ on: await Loomsong.report.ready, db: Loomsong.report.db, small: document.querySelector('.ls-small').textContent }));
    check('off when the host object never comes', z.on === false && z.db === null && !/builder/.test(z.small), `looked for it, found none: off after ${((Date.now() - t0) / 1000).toFixed(1)} s, nothing on the splash`);
  } finally { await Z.close(); }
  const Y = await openPage({ manual: false, init: standIn, query: 'hostapi=loomHost' });
  try {
    const y = await Y.page.evaluate(async () => ({ on: await Loomsong.report.ready, writes: window.__db.writes, mode: Loomsong.clock.mode }));
    check('the address names no host object outside the test clock', y.on === false && y.writes === 0, `a stand-in was present and named in the address, the real audio clock (${y.mode}) was in use: report ${y.on ? 'on' : 'off'}, ${y.writes} writes`);
  } finally { await Y.close(); }

  // ------------------------------------------------------------------ the real page with a stand-in store
  B = await openPage({ manual: true, init: standIn, query: 'hostapi=loomHost' });
  const on = await B.page.evaluate(async () => ({ on: await Loomsong.report.ready, small: document.querySelector('.ls-small').textContent }));
  check('on where there is a store', on.on === true && /tells its builder how it ran/.test(on.small), `ready ${on.on}; the splash says: "${on.small.slice(-100)}"`);
  await B.page.waitForFunction(() => window.__db.writes >= 1, null, { timeout: 60000 });
  const d1 = await B.page.evaluate(() => Object.values(window.__db.store)[0]);
  check('the first document names the browser', d1.version === 1 && /Chrome/.test(d1.env.userAgent) && typeof d1.env.gl.renderer === 'string' && d1.env.gl.renderer.length > 3 && d1.env.viewport[0] === 1280, `${d1.env.userAgent.slice(0, 60)}...; renderer ${d1.env.gl.renderer.slice(0, 60)}`);
  check('it says what the policy allows', typeof d1.policy.wasm === 'string' && /^CompileError/.test(d1.policy.wasm) && d1.policy.blobWorker === 'ok' && d1.violations.some(v => /script-src/.test(v.directive)), `wasm: ${d1.policy.wasm.slice(0, 50)}...; blob worker: ${d1.policy.blobWorker}; ${d1.violations.length} refusal(s) seen (${d1.violations.map(v => v.directive).join(', ')})`);
  check('it times the world and names the clock', d1.pieces.ode && d1.pieces.ode.loadSeconds > 0 && d1.pieces.ode.clock.mode === 'manual', `ode ready in ${d1.pieces.ode && d1.pieces.ode.loadSeconds} s under software GL; clock ${d1.pieces.ode && d1.pieces.ode.clock.mode}`);

  await B.page.evaluate(() => document.querySelector('.ls-big').click());
  await B.frames(6);
  await B.page.waitForFunction(() => Loomsong.report.stats.ode && Loomsong.report.stats.ode.n >= 3, null, { timeout: 120000 });
  await B.page.evaluate(() => Loomsong.pause());
  await B.frames(2);
  await B.page.waitForFunction(() => Object.values(window.__db.store)[0].log.some(l => l[1] === 'pause ode'), null, { timeout: 60000 });
  const d2 = await B.page.evaluate(() => Object.values(window.__db.store)[0]);
  const names = d2.log.map(l => l[1]), ip = names.indexOf('play ode'), iq = names.indexOf('pause ode');
  check('play and pause reach the document', ip > 0 && iq > ip && d2.play.ode && d2.play.ode.frames >= 3 && d2.updatedAt > d1.updatedAt, `log: ${names.join(' | ')}; frames timed ${d2.play.ode && d2.play.ode.frames}, median ${d2.play.ode && d2.play.ode.medianFps} fps (software GL: not a measure of a GPU)`);

  await B.page.evaluate(() => { for (let i = 0; i < 10; i++) Loomsong.report.flush(); });
  await sleep(4500);
  const s = await B.page.evaluate(() => ({ max: window.__db.maxInflight, bytes: window.__db.maxBytes, writes: window.__db.writes, paths: [...new Set(window.__db.paths)] }));
  check('one at a time, small, one document', s.max === 1 && s.bytes < 40000 && s.paths.length === 1 && /^reports\/r[0-9a-z]+$/.test(s.paths[0]), `${s.writes} writes, at most ${s.max} in flight, largest ${s.bytes} bytes (the host allows 262,144), path ${s.paths.join(',')}`);

  await B.page.keyboard.press('2');
  await B.page.waitForFunction(() => Loomsong.piece.id === 'turca' && Loomsong.meta && Loomsong.meta.piece === 'turca', null, { timeout: 120000 });
  await B.page.waitForFunction(() => Object.values(window.__db.store)[0].pieces.turca, null, { timeout: 60000 });
  const d3 = await B.page.evaluate(() => Object.values(window.__db.store)[0]);
  check('switching pieces adds the second', d3.pieces.turca.loadSeconds > 0 && d3.pieces.ode, `turca ready in ${d3.pieces.turca.loadSeconds} s; the first piece's entry is kept`);

  const errs = (await B.page.evaluate(() => Loomsong.errors)).filter(e => !/WebAssembly|wasm/i.test(e));
  const pe = d3.pageErrors.filter(e => !/WebAssembly|wasm/i.test(e));         // X_ITE's tangent generator cannot compile under the strict policy copy: known and harmless
  check('no page errors', errs.length === 0 && B.problems().length === 0 && pe.length === 0, errs.concat(B.problems(), pe).slice(0, 4).join(' | ') || 'none');
} finally {
  const ok = checks.length > 0 && checks.every(c => c.ok);
  fs.writeFileSync(path.join(runs, 'report.json'), JSON.stringify({ witness: 'report', ok, checks }, null, 1));
  if (N) await N.close();
  if (B) await B.close();
  console.log(ok ? 'Report tests green' : 'Report tests RED');
  process.exitCode = ok ? 0 : 1;
}
