#!/usr/bin/env node
// Atlas witness: the dome's motif lookup shows each motif the way up it is in the picture file, and the dome still draws (with its procedural tiles) when the picture does not load.
//   node witnesses/atlas_test.mjs [--probe build/probes/probe_atlas.x3d] [--world build/worlds/turca.x3d] [--runs build/runs]
//
// 1. Orientation. gen/probes/make_atlas_probe.py writes a flat page of the twelve motifs, each drawn through the dome's own motif() lookup (shaders/motif_lib.glsl). The page is photographed in X_ITE and every cell
//    is compared, on a 7 x 7 grid of small windows, with the same motif in art/dome-motifs.jpg: as it is, flipped top to bottom, flipped left to right and turned half way round. The lookup is right when "as it is"
//    is the closest by a wide margin (X_ITE 16.5.1 puts a picture's top row at texture coordinate 0, which is the opposite of the X3D text; this is what holds the shader to it).
// 2. The picture is the one on screen. The Turca's dome, seen from the floor at one time with the picture beside the world and once with the picture missing: the two frames must differ a lot (the atlas reaches
//    the screen), and the frame without it must still be a lit dome (the shader keeps its procedural tiles for any texel whose alpha is not 1), with the failed request the only thing the console complains of.
import fs from 'node:fs';
import path from 'node:path';
import { openStage, frameStats, ROOT } from './stage.mjs';

const argv = process.argv.slice(2);
const arg = (k, d = null) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const probe = path.resolve(arg('probe', path.join(ROOT, 'build', 'probes', 'probe_atlas.x3d')));
const world = path.resolve(arg('world', path.join(ROOT, 'build', 'worlds', 'turca.x3d')));
const runs = path.resolve(arg('runs', path.join(ROOT, 'build', 'runs')));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (name, ok, detail) => { checks.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} ${name}  ${detail}`); };

// ---- 1. orientation -----------------------------------------------------------------------------------------------------------------------------------
{
  const s = await openStage(probe, { W: 1200, H: 900, tag: 'atlas-probe' });
  try {
    await s.at(1, null, null, 8);
    const png = await s.page.screenshot({ type: 'png' });
    const res = await s.page.evaluate(async b64 => {
      const load = src => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => no(new Error('no ' + src.slice(0, 40))); i.src = src; });
      const shot = await load('data:image/png;base64,' + b64), atlas = await load('art/dome-motifs.jpg');
      const ctx = img => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0); return g; };
      const gs = ctx(shot), ga = ctx(atlas);
      const mean = (g, x, y, w) => { const d = g.getImageData(Math.round(x - w / 2), Math.round(y - w / 2), w, w).data; let r = 0, gr = 0, b = 0; for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; } const n = d.length / 4; return [r / n, gr / n, b / n]; };
      const cw = shot.width / 4, ch = shot.height / 3, scale = 480 / cw, N = 7, win = 12, rwin = Math.round(win * scale);
      const out = [];
      for (let t = 0; t < 12; t++) {
        const col = t % 4, row = Math.floor(t / 4);
        const e = { asIs: 0, flipV: 0, flipH: 0, half: 0, other: Infinity };
        const cross = new Array(12).fill(0);
        for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
          const u = (i + 0.5) / N, v = (j + 0.5) / N;
          const a = mean(gs, (col + u) * cw, (row + v) * ch, win);
          const ref = (uu, vv, s = t) => mean(ga, (s % 4) * 512 + 16 + uu * 480, Math.floor(s / 4) * 512 + 16 + vv * 480, rwin);
          const d = b => (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2])) / 3;
          e.asIs += d(ref(u, v)); e.flipV += d(ref(u, 1 - v)); e.flipH += d(ref(1 - u, v)); e.half += d(ref(1 - u, 1 - v));
          for (let s = 0; s < 12; s++) if (s !== t) cross[s] += d(ref(u, v, s));
        }
        for (const k of ['asIs', 'flipV', 'flipH', 'half']) e[k] /= N * N;
        e.other = Math.min(...cross.filter((_, s) => s !== t)) / (N * N);          // the closest any other motif comes to what this cell shows
        out.push(e);
      }
      return out;
    }, png.toString('base64'));
    const sum = k => res.reduce((a, e) => a + e[k], 0) / res.length;
    const tot = { asIs: sum('asIs'), flipV: sum('flipV'), flipH: sum('flipH'), half: sum('half') };
    const worst = Math.max(...res.map(e => e.asIs));
    check('probe: every motif shows the way up it is in the file', worst < 22, `worst tile ${worst.toFixed(1)} of 255 (mean ${tot.asIs.toFixed(1)}; flipped top to bottom ${tot.flipV.toFixed(1)}, left to right ${tot.flipH.toFixed(1)}, half turn ${tot.half.toFixed(1)})`);
    const ident = Math.max(...res.map(e => e.asIs / e.other));
    check('probe: each cell is its own motif and not another', ident < 0.5, `worst cell: own ${res.reduce((a, e) => (e.asIs / e.other > a.r ? { r: e.asIs / e.other } : a), { r: 0 }).r.toFixed(2)} of the nearest other motif's difference (needs under 0.5)`);
    check('probe: the right way up (not flipped top to bottom, not turned half way)', tot.asIs < 0.5 * Math.min(tot.flipV, tot.half), `ratio ${(tot.asIs / Math.min(tot.flipV, tot.half)).toFixed(2)} (needs under 0.5; left to right is not in question, many motifs are mirror symmetric)`);
    const prob = s.problems();
    check('probe: nothing in the console', prob.length === 0, prob.slice(0, 2).join(' | ') || 'clean');
  } finally { await s.close(); }
}

// ---- 2. the picture is the one on screen, and its absence is survivable ------------------------------------------------------------------------------------
{
  const noart = path.join(ROOT, 'build', 'stage-noart');
  fs.rmSync(noart, { recursive: true, force: true });
  fs.mkdirSync(noart, { recursive: true });
  fs.copyFileSync(world, path.join(noart, 'turca.x3d'));                                   // the world alone, with no art folder beside it
  const cam = [0, 1.7, 2.0, 1.5, 12.0, -3.0], T = 63.8;                                    // from the floor, looking up at the dome (section D)
  const shot = async (w, tag) => {
    const s = await openStage(w, { W: 960, H: 540, tag });
    try { await s.at(T, cam, 1.2, 10); const png = await s.page.screenshot({ type: 'png' }); return { png, st: await frameStats(s.page, png), prob: s.problems(), requests: s.srv.log.map(l => l.url + ' ' + l.status) }; }
    finally { await s.close(); }
  };
  const withArt = await shot(world, 'atlas-with');
  const without = await shot(path.join(noart, 'turca.x3d'), 'atlas-without');
  fs.writeFileSync(path.join(runs, 'atlas-with.png'), withArt.png);
  fs.writeFileSync(path.join(runs, 'atlas-without.png'), without.png);
  check('dome: the picture was asked for and served', withArt.requests.some(r => r === 'art/dome-motifs.jpg 200'), withArt.requests.filter(r => r.includes('art/')).join(', ') || 'no request for art/');
  check('dome: a lit dome with the picture', withArt.st.p95 > 0.1 && withArt.st.mean > 0.03, `mean ${withArt.st.mean.toFixed(3)}, p95 ${withArt.st.p95.toFixed(3)}`);
  check('dome: still a lit dome when the picture is missing', without.st.p95 > 0.1 && without.st.mean > 0.03, `mean ${without.st.mean.toFixed(3)}, p95 ${without.st.p95.toFixed(3)}`);
  check('dome: the missing picture shows in the console and nowhere else', without.prob.length > 0 && without.prob.every(p => /dome-motifs|404|Failed to load|not found/i.test(p)), without.prob.slice(0, 2).join(' | ') || 'no complaint at all');
  const s2 = await openStage(path.join(ROOT, 'build', 'probes', 'probe_atlas.x3d'), { W: 320, H: 240, tag: 'atlas-diff' });      // any page does for the pixel arithmetic
  try {
    const diff = await s2.page.evaluate(async ([a, b]) => {
      const load = src => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = 'data:image/png;base64,' + src; });
      const [ia, ib] = await Promise.all([load(a), load(b)]);
      const px = img => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0); return g.getImageData(0, 0, c.width, c.height).data; };
      const da = px(ia), db = px(ib); let s = 0, n = 0;
      for (let i = 0; i < da.length; i += 4 * 5) { s += (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3; n++; }
      return s / n;
    }, [withArt.png.toString('base64'), without.png.toString('base64')]);
    check('dome: with and without the picture are different frames', diff > 12, `mean difference ${diff.toFixed(1)} of 255 (needs over 12)`);
  } finally { await s2.close(); }
}

const ok = checks.every(c => c.ok);
fs.writeFileSync(path.join(runs, 'atlas.json'), JSON.stringify({ witness: 'atlas', ok, checks }, null, 1));
console.log(ok ? `Atlas witness green (${checks.length} checks)` : 'Atlas witness RED');
process.exitCode = ok ? 0 : 1;
