// Moonlight page smoke witness: the built site loads, transforms, plays and moves.
//
//   node moonlight/witnesses/page_smoke.mjs [--site build/pages] [--out build/runs/moonlight]
//
// Serves the built site from a plain static server (what GitHub Pages is), opens /moonlight/ in headless
// Chrome on software GL, and checks: no page errors; the scene arrives (by live XSLT or the stored scene);
// the 4,932 note boxes are in the running X3D; playing moves the playhead and the follow rig; seeking to
// 60 s names the Presto; a still from the middle of the canvas is neither black nor blown out.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const SITE = path.resolve(arg('--site', 'build/pages'));
const OUT = path.resolve(arg('--out', 'build/runs/moonlight'));
fs.mkdirSync(OUT, { recursive: true });

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.xml': 'application/xml',
  '.mp3': 'audio/mpeg', '.mmp': 'application/xml', '.wasm': 'application/wasm', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.woff2': 'font/woff2', '.json': 'application/json', '.md': 'text/markdown' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(SITE, p);
  if (!f.startsWith(SITE) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;

const fails = [], notes = [];
const check = (ok, what) => { (ok ? notes : fails).push(what); console.log(`${ok ? 'ok  ' : 'FAIL'} ${what}`); };

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  '--autoplay-policy=no-user-gesture-required'] });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 860 } });
  const errors = [], missing = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('response', r => { if (r.status() >= 400) missing.push(`${r.status()} ${r.url()}`); });
  await page.goto(`${base}/moonlight/`);
  await page.waitForFunction(() => document.querySelector('#loading').classList.contains('gone') || document.querySelector('#err'),
    null, { timeout: 120000 });
  check(!(await page.$('#err')), 'the page finished loading');
  const mode = await page.innerText('#xsltmode');
  check(/XSLTProcessor|libxslt/.test(mode), `the scene arrived: ${mode.slice(0, 70)}…`);
  const boxes = await page.evaluate(() => {
    const sc = X3D.getBrowser('#canvas').currentScene; let n = 0;
    for (let i = 0; ; i++) { let g; try { g = sc.getNamedNode('LANE_' + i); } catch { break; } n += g.children.length - 1; }
    return n;
  });
  check(boxes === 4932, `note boxes in the running scene: ${boxes}`);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT, 'runway.png') });

  await page.evaluate(() => document.getElementById('play').click());
  await page.waitForTimeout(1200);
  const x0 = await page.evaluate(() => X3D.getBrowser('#canvas').currentScene.getNamedNode('PLAYHEAD').translation.x);
  await page.waitForTimeout(1500);
  const x1 = await page.evaluate(() => X3D.getBrowser('#canvas').currentScene.getNamedNode('PLAYHEAD').translation.x);
  check(x1 > x0, `playing moves the playhead (${x0.toFixed(2)} → ${x1.toFixed(2)})`);
  await page.evaluate(() => { document.getElementById('audio').currentTime = 60; });
  await page.waitForTimeout(2500);
  const sect = await page.innerText('#sect');
  check(/Presto agitato/.test(sect), `60 s is in the Presto: "${sect}"`);
  const rig = await page.evaluate(() => X3D.getBrowser('#canvas').currentScene.getNamedNode('FOLLOW_RIG').translation.x);
  check(rig > 29, `the follow rig travelled with it (x = ${rig.toFixed(1)}, the Presto starts at 29)`);
  const shot = path.join(OUT, 'follow-presto.png');
  await page.screenshot({ path: shot, clip: { x: 520, y: 220, width: 400, height: 300 } });
  const lum = await page.evaluate(async (b64) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += (d[i] + d[i + 1] + d[i + 2]) / 3;
    return s / (d.length / 4);
  }, fs.readFileSync(shot).toString('base64'));
  check(lum > 8 && lum < 235, `a still of the Presto is neither black nor blown out (mean ${lum.toFixed(1)})`);
  check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join(' | ') : ''}`);
  check(missing.length === 0, `no missing files${missing.length ? ': ' + missing.join(' | ') : ''}`);
  // a browser without XSLT (Chrome 158 and later) must get the stored scene, made by the same stylesheet
  const p2 = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const err2 = [];
  p2.on('pageerror', e => err2.push(String(e)));
  await p2.addInitScript(() => { delete window.XSLTProcessor; });
  await p2.goto(`${base}/moonlight/`);
  await p2.waitForFunction(() => document.querySelector('#loading').classList.contains('gone') || document.querySelector('#err'),
    null, { timeout: 120000 });
  const mode2 = await p2.innerText('#xsltmode');
  const boxes2 = await p2.evaluate(() => { const sc = X3D.getBrowser('#canvas').currentScene; let n = 0;
    for (let i = 0; ; i++) { let g; try { g = sc.getNamedNode('LANE_' + i); } catch { break; } n += g.children.length - 1; } return n; });
  check(/libxslt/.test(mode2) && boxes2 === 4932 && err2.length === 0, `without XSLT the stored scene loads (${boxes2} boxes)`);
} finally {
  await browser.close(); server.close();
}
fs.writeFileSync(path.join(OUT, 'smoke.json'), JSON.stringify({ pass: fails.length === 0, ok: notes, fail: fails }, null, 1));
process.exit(fails.length ? 1 : 0);
