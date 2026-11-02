#!/usr/bin/env node
// Hover test: in Learn mode the card the pointer rests on names the right note, for each thing the spec lets you point at: a tapestry thread, a hole in the card chain, a pin, a floor tile.
//   node witnesses/hover_test.mjs [--runs build/runs]
// The camera is placed by the test (the world's free viewpoint) so that the middle of the screen looks straight at a known spot; the pointer goes to the middle; the page's card is read.
// The expected note comes from the score card and the generators' own functions (witnesses/hover_expect.py), not from the page. Frames are software-drawn and slow, so each look waits for the card.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { openPage } from './pagekit.mjs';
import { ROOT } from './stage.mjs';

const runs = path.resolve(process.argv.includes('--runs') ? process.argv[process.argv.indexOf('--runs') + 1] : path.join(ROOT, 'build', 'runs'));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(34) + detail); };
const py = (...a) => execFileSync('python3', ['-I', path.join(ROOT, 'witnesses', 'hover_expect.py'), ...a], { encoding: 'utf8' }).trim().split('\n').map(l => JSON.parse(l));

const A = await openPage({ manual: true });
const P = A.page;
const ev = (fn, arg) => P.evaluate(fn, arg);
const PCN = ['C', 'C♯', 'D', 'E♭', 'E', 'F', 'F♯', 'G', 'A♭', 'A', 'B♭', 'B'];

/** Put the free viewpoint at eye, looking along -Z (down = true: along -Y), with the field of view fov, and rest the pointer in the middle of the screen. Returns the card's text, or null. */
async function look(eye, { down = false, fov = 0.5, t = null } = {}) {
  await ev(([eye, down, fov, t]) => {
    const X = X3D, L = Loomsong;
    if (t !== null) L.clock.setTime(t);
    // The worlds' NavigationInfo keeps X3D's default, a one-second LINEAR transition, and X_ITE starts one every time `set_bind = true` is sent, even to a viewpoint that is already bound; the pointer's pick
    // then reads the old pose until it ends (a few slow frames, a few milliseconds of fast ones: the second floor look read the first tile, here and on a CI runner). A pose set on the bound viewpoint without
    // a bind takes effect at once, which is how the page's rig works (it binds once per grab). The test wants the pose it set, at once, whichever it does.
    const nav = L.browser.currentScene.rootNodes.find(n => { try { return n.getNodeTypeName() === 'NavigationInfo'; } catch (e) { return false; } });
    if (nav) nav.transitionType = new X.MFString('TELEPORT');
    const f = L.nodes.free;
    f.position = new X.SFVec3f(...eye);
    f.orientation = down ? new X.SFRotation(1, 0, 0, -Math.PI / 2) : new X.SFRotation(0, 1, 0, 0);
    f.fieldOfView = fov;
    f.set_bind = true;
  }, [eye, down, fov, t]);
  await A.frames(3);
  const box = await ev(() => { const r = document.querySelector('x3d-canvas').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await P.mouse.move(box[0] - 30, box[1] - 30); await A.frames(2);
  // X_ITE picks when the pointer moves, so a card left over from the last look (a down-looking view of the floor keeps the pointer over the floor) is still showing here. Wait for a sensor hit
  // that comes after this point, not for the card to be showing: the card is then the one for the place aimed at.
  await ev(() => Loomsong.hover.clear());
  const h0 = await ev(() => Loomsong.hover.hits);
  let fresh = false;
  for (let k = 0; k < 4 && !fresh; k++) {
    await P.mouse.move(box[0] + (k % 2), box[1] + (k >> 1));
    try { await P.waitForFunction(h0 => Loomsong.hover.hits > h0 && document.querySelector('.ls-tip').getAttribute('data-show') === '1', h0, { timeout: 15000 }); fresh = true; } catch (e) { /* the next move */ }
  }
  const shown = await ev(() => ({ show: document.querySelector('.ls-tip').getAttribute('data-show'), what: document.querySelector('.ls-tip-what')?.textContent, l1: document.querySelector('.ls-tip-1')?.textContent, l2: document.querySelector('.ls-tip-2')?.textContent, l3: document.querySelector('.ls-tip-3')?.textContent }));
  await P.mouse.move(2, 2); await A.frames(2);
  return fresh && shown.show === '1' ? shown : null;
}
const bye = async () => { await ev(() => Loomsong.nodes.cam.set_bind = true); };

try {
  await ev(() => document.querySelector('.ls-big').click());
  await P.keyboard.press('u');                                              // learn
  check('hash agrees with the shader', await ev(() => Loomsong.meta.map.hash.every(([x, y, h]) => LoomHash2u(x, y) === h)), '8 vectors from the generator reproduced by the page\'s own copy of the hash');

  // ---- Ode: tapestry threads
  const D = await ev(() => Loomsong.D);
  const cands = []; for (let c = 20; c < 250; c += 40) for (let r = 20; r < 380; r += 45) cands.push(`${c},${r}`);
  const exp = py('ode', ...cands);
  const byCode = {};
  for (const e of exp) if (e.code && e.id !== undefined && !byCode[e.code]) byCode[e.code] = e;          // a thread whose row has a note (the card says "no note sounded" otherwise)
  const cells = Object.values(byCode).slice(0, 5);
  let okT = 0, badT = [];
  for (const e of cells) {
    const x = -4 + (e.col + 0.5) / 256 * 8, y = 12.8 - (e.row + 0.5) / 384 * 12;
    const got = await look([x, y, -8.0], { t: D - 5, fov: 0.5 });
    const ok = got && got.what === e.thread + ' thread' && got.l1 === e.line1 && got.l3.startsWith(e.id) && got.l2.includes('bar ' + e.bar) && got.l2.includes(e.who);
    if (ok) okT++; else badT.push(`cell ${e.col},${e.row} wants ${e.thread} / ${e.line1} / ${e.id}, card says ${JSON.stringify(got)}`);
  }
  check('tapestry thread names its note', cells.length >= 4 && okT === cells.length, badT.length ? badT.join(' | ') : `${okT} threads (${cells.map(e => e.thread).join(', ')}) each named the note the shader lights, id and bar and beat included`);
  // a thread that is not woven yet says so
  const unwoven = cells[0];
  const gotU = await look([-4 + (unwoven.col + 0.5) / 256 * 8, 12.8 - (unwoven.row + 0.5) / 384 * 12, -8.0], { t: 1.0, fov: 0.5 });
  check('an unwoven thread says so', gotU && gotU.l1 === 'not yet woven', JSON.stringify(gotU));

  // ---- Ode: the card chain
  const holes = await ev(() => Loomsong.meta.map.hole_rects), bt = await ev(() => Loomsong.meta.notes.map(n => n[3]));
  const tB = 100.0;
  await ev(t => { Loomsong.clock.setTime(t); }, tB); await A.frames(3);
  const bx = await ev(() => Loomsong.browser.currentScene.getNamedNode('Belt').translation.x);
  let k = -1;
  for (let i = 0; i < holes.length; i++) { const wx = bx + (holes[i][0] + holes[i][1]) / 2; if (wx > 1.2 && wx < 2.4 && holes[i][1] - holes[i][0] > 0.08) { k = i; break; } }
  const eB = py('note', 'ode', String(k))[0];
  const gotB = await look([bx + (holes[k][0] + holes[k][1]) / 2, 15.2 + holes[k][2], -20.9], { t: tB, fov: 0.35 });
  check('card chain hole names its note', k >= 0 && gotB && gotB.what === 'hole in the card chain' && gotB.l1 === eB.line1 && gotB.l3.startsWith(eB.id), `aimed at hole ${k} ${eB.id}; card says ${JSON.stringify(gotB)}`);

  // ---- Turca: pins and tiles
  await P.keyboard.press('2'); await P.waitForFunction(() => Loomsong.piece.id === 'turca' && Loomsong.meta.piece === 'turca' && Loomsong.clock.mode === 'manual'); await A.frames(3);
  const m = await ev(() => Loomsong.meta.map);
  const tP = 30.0;
  await ev(t => Loomsong.clock.setTime(t), tP); await A.frames(3);
  const bar = await ev(() => { const b = Loomsong.browser.currentScene.getNamedNode('Barrel'); return { tx: b.translation.x, ty: b.translation.y, tz: b.translation.z, a: b.rotation.angle * Math.sign(b.rotation.x || 1) }; });
  const TAU = Math.PI * 2, wrap = a => { a = ((a + Math.PI) % TAU + TAU) % TAU - Math.PI; return a; };
  let bestPin = -1, bestA = 9, bestAbs = 0;
  m.pins.forEach((p, i) => { const w = wrap(p.th + p.dp / 2 - bar.a); const x = p.x + bar.tx; if (Math.abs(w) < Math.abs(bestA) && Math.abs(x) < 3 && p.dp > 0.012) { bestA = w; bestPin = i; } });
  const pin = m.pins[bestPin], r = m.barrel_r + 0.017;
  const wp = [bar.tx + pin.x, bar.ty + r * Math.sin(bestA), bar.tz + r * Math.cos(bestA)];
  const noteT = await ev(() => Loomsong.meta.notes.map(n => n[3]));
  const pick = pin.notes.reduce((b, n) => Math.abs(noteT[n] - tP) < Math.abs(noteT[b] - tP) ? n : b, pin.notes[0]);
  const eP = py('note', 'turca', String(pick))[0];
  const gotP = await look([wp[0], wp[1], wp[2] + 0.6], { t: tP, fov: 0.3 });
  check('pin names its note', gotP && gotP.what.startsWith('pin on band') && gotP.l1 === eP.line1 && gotP.l3.startsWith(eP.id), `aimed at pin ${bestPin} (head ${pin.src}, ${pin.notes.length} soundings) at ${wp.map(v => v.toFixed(2)).join(' ')}; wants ${eP.line1} ${eP.id}; card says ${JSON.stringify(gotP)}`);

  const f = m.floor, sector = 3, ring = 2, a = sector * TAU / 12, rm = f.r0 + (f.r1 - f.r0) * (ring + 0.5) / f.rings;
  const gotF = await look([rm * Math.sin(a), 1.6, -rm * Math.cos(a)], { down: true, t: 216.0, fov: 0.35 });
  const wantF = `${PCN[(sector * 7) % 12]} · octave ${ring + 2}`;
  check('floor tile names its pitch', gotF && gotF.what === 'floor tile' && gotF.l1 === wantF, `sector ${sector + 1}, ring ${ring}: wants "${wantF}"; card says ${JSON.stringify(gotF)}`);
  // a tile that is lit now names the note that lights it
  const turca = JSON.parse(fs.readFileSync(path.join(ROOT, 'score', 'turca.score.json'), 'utf8'));
  const nn = turca.notes.findIndex((n, i) => n.layer === 'composer' && !n.g && n.t > 60 && n.pitch >= 48 && n.pitch < 96 && turca.notes.filter(o => o.layer === 'composer' && o.pitch === n.pitch && Math.abs(o.t - n.t) < 0.2).length === 1);
  const nt = turca.notes[nn], pc = nt.pitch % 12, sec2 = (pc * 7) % 12, ring2 = Math.floor((nt.pitch - 36) / 12), a2 = sec2 * TAU / 12, r2 = f.r0 + (f.r1 - f.r0) * (ring2 + 0.5) / f.rings;
  const eN = py('note', 'turca', String(nn))[0];
  const gotL = await look([r2 * Math.sin(a2), 1.6, -r2 * Math.cos(a2)], { down: true, t: nt.t + nt.dur * 0.3, fov: 0.35 });
  check('a lit tile names the lighting note', gotL && gotL.what === 'floor tile, lit now' && gotL.l1 === eN.line1 && gotL.l3.startsWith(eN.id), `note ${eN.id} ${eN.line1} at ${nt.t.toFixed(2)} s; card says ${JSON.stringify(gotL)}`);
  await bye();
  const errs = (await ev(() => Loomsong.errors)).filter(e => !/WebAssembly|wasm/i.test(e));
  check('no page errors', errs.length === 0 && A.problems().length === 0, errs.concat(A.problems()).slice(0, 4).join(' | ') || 'none');
} finally {
  const ok = checks.length > 0 && checks.every(c => c.ok);
  fs.writeFileSync(path.join(runs, 'hover.json'), JSON.stringify({ witness: 'hover', ok, checks }, null, 1));
  await A.close();
  console.log(ok ? 'Hover tests green' : 'Hover tests RED');
  process.exitCode = ok ? 0 : 1;
}
