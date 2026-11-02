#!/usr/bin/env node
// Eyes witness (spec): twelve stills per world at fixed score times, none of them black and none blown out (95th luminance percentile under 0.98).
//   node witnesses/eyes.mjs --world build/worlds/turca.x3d [--size 1280x720] [--out build/stills/eyes] [--runs build/runs]
// The twelve times are (k + 0.5) / 12 of the piece, so they are the same for every build of a piece. "Black" is a frame with almost no light anywhere (95th percentile under 0.03 or mean under 0.02);
// "flat" is one whose luminance never varies (95th percentile minus median under 0.01). The picture judge and his eye are the other two parts of the witness: this script writes the frames and
// a contact-sheet list for them and reports only what a program can know. Frame rates here are software-rendered and mean nothing.
import fs from 'node:fs';
import path from 'node:path';
import { openStage, frameStats, shaderNames, ROOT } from './stage.mjs';

const argv = process.argv.slice(2);
const arg = (k, d = null) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const world = path.resolve(arg('world'));
const name = path.basename(world, '.x3d');
const out = path.resolve(arg('out', path.join(ROOT, 'build', 'stills', 'eyes-' + name)));
const runs = path.resolve(arg('runs', path.join(ROOT, 'build', 'runs')));
const [W, H] = arg('size', '1280x720').split('x').map(Number);
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync(runs, { recursive: true });

const s = await openStage(world, { W, H, tag: 'eyes-' + name });
const rows = [];
try {
  const D = await s.page.evaluate(() => window.stage.duration());
  for (let k = 0; k < 12; k++) {
    const t = Math.round(D * (k + 0.5) / 12 * 1000) / 1000;
    await s.at(t, null, null, 8);
    const png = await s.page.screenshot({ type: 'png' });
    const file = path.join(out, `${name}-eyes-${String(k + 1).padStart(2, '0')}.png`);
    fs.writeFileSync(file, png);
    const st = await frameStats(s.page, png);
    const black = st.p95 < 0.03 || st.mean < 0.02, blown = st.p95 >= 0.98, flat = st.p95 - st.p50 < 0.01;
    rows.push({ k: k + 1, t, file: path.relative(ROOT, file), ...st, black, blown, flat, ok: !black && !blown && !flat });
    console.log(`${rows[k].ok ? 'PASS' : 'FAIL'} still ${String(k + 1).padStart(2)}  t=${t.toFixed(1).padStart(6)}  mean ${st.mean.toFixed(3)}  p50 ${st.p50.toFixed(3)}  p95 ${st.p95.toFixed(3)}  black px ${(st.black * 100).toFixed(0)}%${black ? '  BLACK' : ''}${blown ? '  BLOWN' : ''}${flat ? '  FLAT' : ''}`);
  }
} finally {
  const prob = s.problems();
  const ok = rows.length === 12 && rows.every(r => r.ok) && prob.length === 0;
  fs.writeFileSync(path.join(runs, `eyes-${name}.json`), JSON.stringify({ witness: 'eyes', world: path.relative(ROOT, world), size: [W, H], ok, rows, console: prob, note: 'the picture judge and the owner are the other parts of this witness; his eye is the judge of record' }, null, 1));
  await s.close();
  console.log(ok ? `Eyes (program part) green for ${name}` : `Eyes RED for ${name}${prob.length ? ': ' + prob.slice(0, 3).join(' | ') : ''}`);
  process.exitCode = ok ? 0 : 1;
}
