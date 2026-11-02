#!/usr/bin/env node
// Render stills of a world at given score times, in headless Chrome under the policy copy, and write luminance facts beside them.
//   node witnesses/stills.mjs --world build/worlds/turca.x3d --times 12,60,150 [--out build/stills/turca] [--size 1280x720] [--cam "x y z  tx ty tz"] [--fov 60] [--name shot]
// The page is the bare stage of stage.mjs. --cam overrides the directed camera after the time is set (a position and a look-at target); without it the stills show what the directed track does.
// Output: <out>/<name>-<t>.png and <out>/stills.json {file, t, mean, p95, black, console}. Frame rates measured here are software-rendered and mean nothing (spec: Fps).
import fs from 'node:fs';
import path from 'node:path';
import { openStage, frameStats, shaderNames, ROOT } from './stage.mjs';

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

fs.mkdirSync(out, { recursive: true });
const s = await openStage(world, { W, H });
const rows = [];
try {
  console.log('loaded in', s.loadSeconds.toFixed(1), 's', JSON.stringify(s.info));
  const sv = await s.page.evaluate(n => window.stage.shaders(n), shaderNames(world));
  const bad = sv.filter(x => x.valid !== true);
  console.log(`shaders ${sv.length}, valid ${sv.length - bad.length}${bad.length ? ', NOT VALID: ' + bad.map(x => x.name).join(' ') : ''}`);
  for (const t of times) {
    const t1 = Date.now();
    await s.at(t, cam, fov, settle);
    const png = await s.page.screenshot({ type: 'png' });
    const file = path.join(out, `${name}-${String(t).replace('.', '_')}.png`);
    fs.writeFileSync(file, png);
    const stats = await frameStats(s.page, png);
    rows.push({ file: path.relative(ROOT, file), t, ...stats });
    console.log(`t=${t}  mean ${stats.mean.toFixed(3)}  median ${stats.p50.toFixed(3)}  p95 ${stats.p95.toFixed(3)}  black ${(stats.black * 100).toFixed(0)}%  ${((Date.now() - t1) / 1000).toFixed(1)} s  ${path.relative(ROOT, file)}`);
  }
} finally {
  const bad = s.problems();
  fs.writeFileSync(path.join(out, 'stills.json'), JSON.stringify({ world: path.relative(ROOT, world), size: [W, H], rows, console: bad, csp: s.rec.csp }, null, 1));
  if (bad.length) console.log('CONSOLE', bad.slice(0, 12).join('\n  '));
  await s.close();
}
