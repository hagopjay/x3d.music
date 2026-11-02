#!/usr/bin/env node
// Behaviour witness (spec): the world loads in X_ITE 16.5.1 headless under the policy copy; the console is clean; no shader fails to compile; every ROUTE fires when the bus moves.
//   node witnesses/behaviour.mjs --world build/worlds/ode.x3d [--out build/runs] [--steps 24]
// "Fires" is measured, not assumed: every ROUTE's source field gets a callback, the bus is set to `steps` fractions of the piece (spread over the whole of it, ends included), and each
// distinct source field must have produced events; a route whose value never changed over the sweep is listed (it may be legitimate: a constant interpolator) and counted as "still".
// Exit 1 on any red check. The run record is <out>/behaviour-<world>.json.
import fs from 'node:fs';
import path from 'node:path';
import { openStage, shaderNames, ROOT } from './stage.mjs';
import { harmless } from './harness.mjs';

const argv = process.argv.slice(2);
const arg = (k, d = null) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const world = path.resolve(arg('world'));
const outDir = path.resolve(arg('out', path.join(ROOT, 'build', 'runs')));
const steps = Number(arg('steps', '24'));
const name = path.basename(world, '.x3d');
fs.mkdirSync(outDir, { recursive: true });

const s = await openStage(world, { W: 640, H: 360, tag: 'behaviour-' + name });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(22) + detail); };
let sweep = null;
try {
  const names = shaderNames(world);
  const version = await s.page.evaluate(() => X3D.getBrowser(document.getElementById('c')).getVersion());
  check('loads', version === '16.5.1', `X_ITE ${version}, scene current in ${s.loadSeconds.toFixed(1)} s, renderer ${s.info.renderer}`);

  const sv = await s.page.evaluate(n => window.stage.shaders(n), names);
  const bad = sv.filter(x => x.valid !== true);
  check('shaders compile', sv.length > 0 && !bad.length, `${sv.length - bad.length} of ${sv.length} ComposedShaders valid${bad.length ? ' (NOT: ' + bad.map(x => x.name).join(' ') + ')' : ''}`);

  sweep = await s.page.evaluate(async (steps) => {
    const B = X3D.getBrowser(document.getElementById('c'));
    const sc = B.currentScene;
    const D = window.stage.duration();
    const bus = window.stage.node('FractionBus');
    const sec = window.stage.node('SecondsBus');
    const clock = window.stage.node('Clock');
    const seen = new Map();                                    // "Node.field" -> { n, values: Set(of short strings), node, field }
    const label = (n) => (n.getNodeName() || n.getTypeName()) + '.';
    const routes = [];
    for (const r of sc.routes) {
      const k = label(r.sourceNode) + r.sourceField;
      routes.push({ from: k, to: label(r.destinationNode) + r.destinationField });
      if (seen.has(k)) continue;
      const rec = { n: 0, values: new Set(), node: r.sourceNode, field: r.sourceField };
      seen.set(k, rec);
      r.sourceNode.addFieldCallback('behaviour:' + k, r.sourceField, v => { rec.n++; rec.values.add(String(v).slice(0, 80)); });
    }
    // the standalone clock: ship disabled (the page owns time); run it for a moment to see that its ROUTE feeds the bus, then switch it off as the page does
    const now = Date.now() / 1000;
    clock.enabled = true; clock.stopTime = now; clock.startTime = now + 0.05;
    await new Promise(r => setTimeout(r, 700));
    await window.stage.frames(4);
    const clockEvents = seen.get('Clock.fraction_changed').n;
    clock.enabled = false;
    await window.stage.frames(2);
    const fracs = [];
    for (let i = 0; i < steps; i++) fracs.push(i / (steps - 1));
    const secErr = [];
    for (const f of fracs) {
      bus.set_fraction = f;
      await window.stage.frames(3);
      secErr.push(Math.abs(sec.value_changed - f * D));
    }
    // a route whose value stayed put over those settings (a strike is a third of a second wide, so evenly spaced samples can miss it) is exercised again at a keyed time where its own keys differ
    const proved = [];
    for (const [k, r] of seen) {
      if (r.n === 0 || r.values.size > 1) continue;
      const node = r.node;
      if (!node.key || !node.keyValue || node.key.length < 2) continue;
      let at = null;
      for (let i = 0; i + 1 < node.key.length && at === null; i++) if (String(node.keyValue[i]) !== String(node.keyValue[i + 1])) at = (node.key[i] + node.key[i + 1]) / 2;
      if (at === null) continue;
      bus.set_fraction = at;
      await window.stage.frames(3);
      if (r.values.size > 1) proved.push(k);
    }
    const per = [...seen.entries()].map(([k, r]) => ({ k, events: r.n, distinct: r.values.size }));
    return { routes: routes.length, sources: per.length, per, D, secErr: Math.max(...secErr), clockEvents, proved };
  }, steps);
  const silent = sweep.per.filter(p => p.events === 0);
  const still = sweep.per.filter(p => p.events > 0 && p.distinct < 2 && !sweep.proved.includes(p.k));
  check('every ROUTE fires', sweep.routes > 0 && !silent.length && sweep.clockEvents > 5, `${sweep.routes} ROUTEs from ${sweep.sources} source fields; the standalone Clock gave ${sweep.clockEvents} events in 0.7 s; ${steps} settings of the bus; silent: ${silent.length ? silent.map(p => p.k).join(', ') : 'none'}`);
  check('every ROUTE moves', still.length === 0, `${sweep.sources - still.length} of ${sweep.sources} source fields changed value (${sweep.proved.length} only at a keyed time, where their own keys differ: ${sweep.proved.join(', ') || 'none'}); never moved: ${still.length ? still.map(p => p.k).join(', ') : 'none'}`);
  check('bus is exact', sweep.secErr < 1e-6, `SecondsBus = fraction x D to ${sweep.secErr.toExponential(2)} s over the sweep (D ${sweep.D.toFixed(3)} s)`);
  await s.at(sweep.D * 0.5, null, null, 4);
  const png = await s.page.screenshot({ type: 'png' });
  check('draws', png.length > 20000, `a mid-piece frame of ${png.length} bytes`);
  const prob = s.problems();
  check('console clean', prob.length === 0, prob.length ? prob.slice(0, 6).join(' | ') : `no error or warning in ${s.rec.console.length} console lines; ${s.rec.failed.length} failed requests; ${s.rec.http.length} HTTP errors`);
  const csp = await s.rec.collectCsp();
  const cspBad = csp.filter(x => !harmless(x));
  check('policy copy', cspBad.length === 0, cspBad.length ? cspBad.join(' | ') : `${csp.length} refusals, all the known harmless ones`);
} finally {
  const ok = checks.length > 0 && checks.every(c => c.ok);
  fs.writeFileSync(path.join(outDir, `behaviour-${name}.json`), JSON.stringify({ witness: 'behaviour', world: path.relative(ROOT, world), xite: '16.5.1', browser: s.L.chrome, ok, checks, sweep }, null, 1));
  await s.close();
  console.log(ok ? `Behaviour green for ${name}` : `Behaviour RED for ${name}`);
  process.exitCode = ok ? 0 : 1;
}
