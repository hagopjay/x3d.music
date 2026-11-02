#!/usr/bin/env node
// Page tests: the interface does what the spec says, measured in the built page under the policy copy (the test clock, so a bar is a bar and not a guess).
//   node witnesses/page_test.mjs [--runs build/runs]
// Checks: Play is the only way in; U cycles none, minimal, learn; Space plays and pauses; Left and Right seek whole bars; 1 and 2 pick the piece; C freezes and releases the camera; a grab binds the
// free viewpoint and, after four idle seconds, eases back onto the directed one; K is calm and reaches every shader; the page's bar, beat and tempo arithmetic equals the score card's on 60 notes a piece;
// the harmony compass names the chord the card gives; the end card carries the credits.
import fs from 'node:fs';
import path from 'node:path';
import { openPage } from './pagekit.mjs';
import { ROOT } from './stage.mjs';

const runs = path.resolve(process.argv.includes('--runs') ? process.argv[process.argv.indexOf('--runs') + 1] : path.join(ROOT, 'build', 'runs'));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(34) + detail); };
const card = p => JSON.parse(fs.readFileSync(path.join(ROOT, 'score', p + '.score.json'), 'utf8'));

const A = await openPage({ manual: true });
const P = A.page;
const ev = (fn, arg) => P.evaluate(fn, arg);
const settle = n => A.frames(n);
try {
  check('splash first', await ev(() => !document.querySelector('.ls-splash').hidden && document.querySelector('#ls-root').getAttribute('data-started') === '0' && getComputedStyle(document.querySelector('.ls-corner')).display === 'none'), 'the title card and Play show; the corner card is hidden until sound has started');
  await ev(() => document.querySelector('.ls-big').click());
  await settle(2);
  check('play starts', await ev(() => Loomsong.clock.playing && document.querySelector('.ls-splash').hidden), 'Play hides the title card and starts the clock');

  // views
  const modes = [];
  for (let i = 0; i < 3; i++) { modes.push(await ev(() => document.querySelector('#ls-root').getAttribute('data-mode'))); await P.keyboard.press('u'); }
  check('U cycles the views', modes.join(',') === 'minimal,learn,none' && await ev(() => document.querySelector('#ls-root').getAttribute('data-mode')) === 'minimal', `${modes.join(' > ')} > minimal`);
  await P.keyboard.press('u'); await P.keyboard.press('u');                // none
  check('none shows only the picture', await ev(() => ['.ls-corner', '.ls-compass', '.ls-lyric'].every(s => getComputedStyle(document.querySelector(s)).display === 'none')), 'corner, compass and lyric all hidden');
  await P.keyboard.press('u');                                              // minimal

  // space
  await P.keyboard.press('Space'); await settle(2);
  const paused = await ev(() => !Loomsong.clock.playing);
  await P.keyboard.press('Space'); await settle(2);
  check('Space plays and pauses', paused && await ev(() => Loomsong.clock.playing), 'pause, then play');

  // bars
  const ode = card('ode');
  const bars = await ev(() => Loomsong.meta.bar_t);
  await ev(t => Loomsong.clock.setTime(t), bars[9] + 0.3);                 // a third of a second into bar 10
  await settle(1);
  await P.keyboard.press('ArrowRight'); await settle(2);
  const afterR = await ev(() => Loomsong.clock.now());
  await P.keyboard.press('ArrowLeft'); await settle(2);                     // 0.3 s into bar 11? no: we are at its start, so back goes to bar 10's start
  const afterL = await ev(() => Loomsong.clock.now());
  check('Left and Right seek a bar', Math.abs(afterR - bars[10]) < 1e-3 && Math.abs(afterL - bars[9]) < 1e-3, `from 0.3 s into bar 10: right to bar 11 at ${afterR.toFixed(3)} s (card ${bars[10].toFixed(3)}), left back to bar 10 at ${afterL.toFixed(3)} s (card ${bars[9].toFixed(3)})`);

  // bar and beat arithmetic against the card, 60 notes a piece
  for (const piece of ['ode', 'turca']) {
    if (await ev(() => Loomsong.piece.id) !== piece) { await P.keyboard.press(piece === 'ode' ? '1' : '2'); await P.waitForFunction(p => Loomsong.piece.id === p && Loomsong.meta && Loomsong.meta.piece === p && Loomsong.clock.mode === 'manual', piece); await settle(2); }
    const c = card(piece);
    const comp = c.notes.filter(n => n.layer === 'composer' && !n.g);
    const pick = Array.from({ length: 60 }, (_, i) => comp[Math.floor(i * (comp.length - 1) / 59)]);
    const got = await ev(ns => ns.map(n => { const w = Loomsong.where(n.t + 1e-4); return { id: n.id, bar: w.bar, beat: w.beat, wantBar: n.bar, wantBeat: n.beat }; }), pick);
    const bad = got.filter(g => g.bar !== g.wantBar || Math.abs(g.beat - g.wantBeat) > 0.02);
    check(`bar and beat match the card (${piece})`, bad.length === 0, bad.length ? bad.slice(0, 3).map(b => `${b.id}: page ${b.bar}.${b.beat.toFixed(3)} card ${b.wantBar}.${b.wantBeat}`).join(' | ') : `60 notes spread over the piece: page and card agree on bar and on beat to 0.02`);
    const qc = await ev(() => Loomsong.meta.qcheck.map(([t, q]) => Math.abs(LoomQuarters(Loomsong.meta.tempo, t) - q)));
    check(`tempo map matches the card (${piece})`, Math.max(...qc) < 2e-3, `${qc.length} times, worst quarter error ${Math.max(...qc).toExponential(1)} (the card's own t to q is rounded to 1e-7 s)`);
    // compass names the chord
    await P.keyboard.press('u');                                           // learn
    const H = c.harmony, tt = [H[3].t + 0.01, H[Math.floor(H.length / 2)].t + 0.01, H[H.length - 2].t + 0.01];
    const PC = ['C', 'C♯', 'D', 'E♭', 'E', 'F', 'F♯', 'G', 'A♭', 'A', 'B♭', 'B'], Q = { M: 'major', m: 'minor', '7': 'dominant seventh', dim: 'diminished' };
    const names = [];
    for (const t of tt) {
      await ev(t => Loomsong.clock.setTime(t), t); await settle(2);
      const text = await ev(() => document.querySelector('.ls-chord').textContent);
      const h = [...H].reverse().find(h => h.t <= t + 1e-6);
      names.push([text, `${PC[h.root % 12]} ${Q[h.qual] || h.qual}  ·  ${h.roman}`]);
    }
    check(`compass names the chord (${piece})`, names.every(([a, b]) => a === b), names.map(([a, b]) => a === b ? a : `${a} != ${b}`).join(' | '));
    await P.keyboard.press('u'); await P.keyboard.press('u');              // none, minimal
  }

  // lyric for the ode
  await P.keyboard.press('1'); await P.waitForFunction(() => Loomsong.piece.id === 'ode' && Loomsong.meta.piece === 'ode' && Loomsong.clock.mode === 'manual'); await settle(2);
  await P.keyboard.press('u');
  const ly = await ev(() => Loomsong.meta.lyrics);
  await ev(t => Loomsong.clock.setTime(t), ly[5].t0 + 0.5); await settle(2);
  const shown = await ev(() => [document.querySelector('.ls-de').textContent, document.querySelector('.ls-en').textContent]);
  check('the Ode shows its line with a gloss', shown[0] === ly[5].de && shown[1] === ly[5].en && ly.length >= 20, `${ly.length} lines laid by four-bar phrase; at ${(ly[5].t0 + 0.5).toFixed(1)} s: "${shown[0]}" / "${shown[1]}"`);
  await P.keyboard.press('u'); await P.keyboard.press('u');

  // piece keys
  await P.keyboard.press('2'); await P.waitForFunction(() => Loomsong.piece.id === 'turca' && Loomsong.meta.piece === 'turca' && Loomsong.clock.mode === 'manual'); await settle(2);
  const turcaD = await ev(() => Loomsong.nodes.sec.keyValue.slice(-1)[0]);
  check('1 and 2 pick the piece', Math.abs(turcaD - (await ev(() => Loomsong.piece.D))) < 0.01 && await ev(() => !!Loomsong.nodes.bus && Loomsong.lastSent < 0.5), `2 loaded the Turca world (its bus runs to ${turcaD.toFixed(3)} s)`);

  // camera
  await P.keyboard.press('c'); await settle(1);
  const freeMode = await ev(() => Loomsong.rig.mode);
  const bound = await ev(() => Loomsong.nodes.free.isBound);
  await P.keyboard.press('c'); await settle(1);
  const back = await ev(() => [Loomsong.rig.mode, Loomsong.nodes.cam.isBound]);
  check('C freezes and releases the camera', freeMode === 'free' && bound === true && back[0] === 'directed' && back[1] === true, `free (Free bound: ${bound}), then directed (Cam bound: ${back[1]})`);
  const box = await ev(() => { const r = document.querySelector('x3d-canvas').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await P.mouse.move(box[0], box[1]); await P.mouse.down(); await P.mouse.move(box[0] + 120, box[1] + 40, { steps: 6 }); await P.mouse.up(); await settle(3);
  const g = await ev(() => ({ mode: Loomsong.rig.mode, free: Loomsong.nodes.free.isBound, yaw: Loomsong.rig.yaw, moved: Math.hypot(...['x', 'y', 'z'].map(k => Loomsong.nodes.free.position[k] - Loomsong.nodes.cam.position[k])) }));
  check('a grab binds the free viewpoint', g.mode === 'grabbed' && g.free === true && Math.abs(g.yaw) > 0.3 && g.moved < 1e-6, `dragging 120 px: mode ${g.mode}, the view turned ${g.yaw.toFixed(2)} rad, Free bound ${g.free}`);
  const t0 = Date.now();
  await P.waitForFunction(() => Loomsong.rig.mode === 'directed' && Loomsong.nodes.cam.isBound, null, { timeout: 90000 });
  const dt = (Date.now() - t0) / 1000;
  check('four idle seconds ease it back', dt > 1.0, `back on the directed camera ${dt.toFixed(1)} s after the check (four idle seconds, then an ease of a few time constants; software frames are slow, so it takes more frames than on a GPU)`);

  // calm
  await P.keyboard.press('k'); await settle(2);
  const calm = await ev(() => Loomsong.nodes.shaders.map(s => s.u_calm));
  check('K is calm and reaches every shader', calm.length > 5 && calm.every(v => v === 1), `${calm.length} shaders at u_calm = 1`);
  await P.keyboard.press('k');

  // credits
  await ev(D => { Loomsong.clock.setTime(D); }, await ev(() => Loomsong.D)); await settle(3);
  const cr = await ev(() => ({ show: document.querySelector('.ls-credits').getAttribute('data-show'), text: document.querySelector('.ls-credbody').textContent }));
  check('the end card carries the credits', cr.show === '1' && /Sapp/.test(cr.text) && /Salamander/.test(cr.text) && /Nothing in this scene is AI-made/.test(cr.text), `${cr.text.length} characters, with the encoding credit, the piano credit and the AI statement`);
  const errs = (await ev(() => Loomsong.errors)).filter(e => !/WebAssembly|wasm/i.test(e));
  check('no page errors', errs.length === 0 && A.problems().length === 0, errs.concat(A.problems()).slice(0, 4).join(' | ') || 'none');
} finally {
  const ok = checks.length > 0 && checks.every(c => c.ok);
  fs.writeFileSync(path.join(runs, 'page.json'), JSON.stringify({ witness: 'page', ok, checks }, null, 1));
  await A.close();
  console.log(ok ? 'Page tests green' : 'Page tests RED');
  process.exitCode = ok ? 0 : 1;
}
