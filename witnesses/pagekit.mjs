// Open the built page (build/page) the way the host serves it: its own files only, a skeleton around index.html, .x3d as application/xml, the strict policy copy on every response.
// Used by the Host witness and the page tests. manual: the clock is set by hand (?clock=manual) so a whole piece can be stepped through; false uses the real audio clock.
import fs from 'node:fs';
import path from 'node:path';
import { startServer, launch, instrument, harmless } from './harness.mjs';
import { ROOT, abortedAfterServed } from './stage.mjs';

export const PAGE = path.join(ROOT, 'build', 'page');

export async function openPage({ manual = true, size = [1280, 720], hash = '', csp = undefined } = {}) {
  const manifest = JSON.parse(fs.readFileSync(path.join(PAGE, 'manifest.json'), 'utf8'));
  const published = new Set(manifest.files.map(f => f.path));
  const srv = await startServer({ root: PAGE, published, ...(csp ? { csp } : {}) });
  const L = await launch();
  const context = await L.browser.newContext({ viewport: { width: size[0], height: size[1] }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.setDefaultTimeout(180000);
  const rec = await instrument(page, srv.base);
  const t0 = Date.now();
  await page.goto(srv.base + 'index.html' + (manual ? '?clock=manual' : '') + (hash ? '#' + hash : ''), { waitUntil: 'load' });
  await page.waitForFunction(() => window.Loomsong && window.Loomsong.ready, null, { timeout: 120000 });
  await page.evaluate(() => window.Loomsong.ready);
  return {
    page, rec, srv, L, manifest, loadSeconds: (Date.now() - t0) / 1000,
    frames: n => page.evaluate(n => new Promise(res => { let i = 0; const f = () => (++i >= n ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); }), n),
    /** Console lines and requests that count against the page: not the known harmless ones, and not a request cut after the server had answered it. */
    problems() { return [...rec.errors, ...rec.console.filter(s => /^(error|warning)/.test(s)), ...rec.failed, ...rec.http].filter(s => !harmless(s) && !abortedAfterServed(s, srv.log)); },
    async close() { await rec.collectCsp().catch(() => {}); await L.browser.close(); await srv.close(); },
  };
}
