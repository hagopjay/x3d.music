// Test harness shared by the Behaviour, Host, Eyes, Sync and Fps witnesses and the probes.
//   - startServer(): serves a build directory the way the host serves a published page, as far as this container can copy it:
//     the page goes inside a skeleton like the host's, .x3d goes out as application/xml, only published files are served, and every
//     response carries a strict CSP written from the Artifact page contract (scripts from 'self', inline and five CDNs; fetch only from
//     'self'; no 'unsafe-eval'). The real host's policy is not visible from here, so a pass is C under the copy and L on the real host.
//   - launch(): headless Chrome with software GL by default (LOOM_GL=swiftshader) or the machine's GPU (LOOM_GL=gpu).
//   - instrument(): console, page errors, failed requests, HTTP errors and CSP violations, kept per page.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

export const CDNS = 'https://cdnjs.cloudflare.com https://cdn.jsdelivr.net/npm/ https://unpkg.com https://cdn.tailwindcss.com https://code.jquery.com';
export const CSP = [
  "default-src 'none'",
  "script-src 'self' 'unsafe-inline' " + CDNS,
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  'font-src https://fonts.gstatic.com',
  "img-src 'self' data: blob:",
  "connect-src 'self'",
  "worker-src 'self' blob:",
  "media-src 'self' data: blob:",
].join('; ');

/** The same policy with WebAssembly compile allowed: the variant that tells whether a feature needs 'wasm-unsafe-eval' (X_ITE's splat sorter does). */
export const CSP_WASM = CSP.replace("script-src 'self'", "script-src 'self' 'wasm-unsafe-eval'");

const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.x3d': 'application/xml', '.xml': 'application/xml', '.txt': 'text/plain', '.md': 'text/markdown', '.wasm': 'application/wasm',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml',
  '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.mp4': 'audio/mp4', '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.webm': 'video/webm',
};
const SKELETON = [
  '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
  '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}',
  'img{max-width:100%}[hidden]{display:none!important}</style></head><body>', '</body></html>'];

/** Serve `root`. published: a Set of relative paths that ship (index.html is always served); omit to serve everything under root. */
export function startServer({ root, published = null, wrapIndex = true, mime = {}, csp = CSP }) {
  root = path.resolve(root);
  const log = [];
  const srv = http.createServer((req, rsp) => {
    const u = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html';
    const f = path.join(root, u);
    const hdr = { 'content-security-policy': csp, 'cache-control': 'no-store' };
    if (u === 'favicon.ico') { rsp.writeHead(204, hdr); rsp.end(); return; }
    const ok = f.startsWith(root) && fs.existsSync(f) && fs.statSync(f).isFile() && (!published || published.has(u) || u === 'index.html');
    log.push({ url: u, status: ok ? 200 : 404, range: req.headers.range || null });
    if (!ok) { rsp.writeHead(404, hdr); rsp.end('not found'); return; }
    let body = fs.readFileSync(f);
    const type = mime[path.extname(f)] || TYPES[path.extname(f)] || 'application/octet-stream';
    if (u === 'index.html' && wrapIndex) body = Buffer.from(SKELETON.slice(0, 3).join('') + body.toString('utf8') + SKELETON[3]);
    const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
    if (m && type.startsWith('audio/')) {                                   // media elements ask for ranges
      const a = m[1] === '' ? Math.max(0, body.length - Number(m[2])) : Number(m[1]);
      const b = m[1] !== '' && m[2] !== '' ? Math.min(Number(m[2]), body.length - 1) : body.length - 1;
      rsp.writeHead(206, { ...hdr, 'content-type': type, 'accept-ranges': 'bytes', 'content-range': `bytes ${a}-${b}/${body.length}`, 'content-length': b - a + 1 });
      rsp.end(body.subarray(a, b + 1)); return;
    }
    rsp.writeHead(200, { ...hdr, 'content-type': type, 'accept-ranges': 'bytes', 'content-length': body.length });
    rsp.end(body);
  });
  return new Promise(res => srv.listen(0, '127.0.0.1', () => res({
    base: 'http://127.0.0.1:' + srv.address().port + '/', log, close: () => new Promise(r => srv.close(r)),
  })));
}

export async function launch({ gl = process.env.LOOM_GL || 'swiftshader' } = {}) {
  const args = ['--no-sandbox', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run'];
  if (gl === 'swiftshader') args.push('--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader');
  else args.push('--use-gl=angle', '--use-angle=gl-egl', '--enable-gpu-rasterization');
  // GEN_CHROME names a binary. Otherwise ask Playwright for its full Chrome for Testing in the new headless mode (channel 'chromium'),
  // not the old headless shell it would pick by default: the sandbox and CI then run the same browser build (pins.json: browser).
  const executablePath = process.env.GEN_CHROME || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath, args } : { channel: 'chromium', args });
  return { browser, gl, chrome: browser.version(), playwright: require('playwright/package.json').version };
}

/** Attach listeners; returns the record object that fills as the page runs. */
export async function instrument(page, base) {
  const rec = { console: [], errors: [], failed: [], http: [], csp: [] };
  await page.addInitScript(() => {
    window.__csp = [];
    document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI));
  });
  page.on('console', m => rec.console.push(m.type() + ': ' + m.text().slice(0, 300)));
  page.on('pageerror', e => rec.errors.push(String(e).slice(0, 300)));
  page.on('requestfailed', q => rec.failed.push(q.url().replace(base, '') + ' ' + ((q.failure() || {}).errorText || '')));
  page.on('response', q => { if (q.status() >= 400) rec.http.push(q.url().replace(base, '') + ' HTTP ' + q.status()); });
  rec.collectCsp = async () => { rec.csp = await page.evaluate(() => window.__csp || []); return rec.csp; };
  return rec;
}

/** Known and harmless under the copy of the policy (X_ITE's own UI font; its tangent wasm compile): see FACTS in x3d.onto, section P. */
export const harmless = s => /PT_Sans|PTSans|wasm|WebAssembly|CompileError|favicon/i.test(s);

/** Decode a PNG buffer in the page and read RGBA at points (the page's img-src allows data:). */
export async function samplePixels(page, png, points) {
  return page.evaluate(async ([b64, pts]) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
    return pts.map(([x, y]) => Array.from(g.getImageData(x, y, 1, 1).data));
  }, [png.toString('base64'), points]);
}

export const sleep = ms => new Promise(r => setTimeout(r, ms));
