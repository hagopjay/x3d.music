#!/usr/bin/env node
// Cards test: the animated pictures (page/cards.js) do what they are for, in the built page under the policy copy, and the music never waits for one.
//   node witnesses/cards_test.mjs [--runs build/runs]
// The page is built with cards in it (CI and this test use the four test patterns from tools/prep_cards.py --synthetic: two-second videos that say what they are; a build with the real,
// AI-made cards runs the same code and the same checks, and its words say AI-made instead). The test clock is on, and cards=on in the address asks for them under it (they are left out otherwise).
// Checks: with the test clock and no cards=on, no card is made; the title card is a muted video behind the title and Play; Play starts the clock at once and the opening card covers the world with the
// piece's name, then dissolves on its own timer; it plays once, not again after a pause; Escape ends one early; Calm leaves the opening out; the end card has the in-between picture behind it;
// the page copes when the video files do not arrive (the poster shows, the clock runs, only the failed requests are reported); the words say what is AI-made and never call a test pattern that.
import fs from 'node:fs';
import path from 'node:path';
import { openPage } from './pagekit.mjs';
import { ROOT } from './stage.mjs';

const runs = path.resolve(process.argv.includes('--runs') ? process.argv[process.argv.indexOf('--runs') + 1] : path.join(ROOT, 'build', 'runs'));
fs.mkdirSync(runs, { recursive: true });
const checks = [];
const check = (id, ok, detail) => { checks.push({ id, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + id.padEnd(40) + detail); };
const cfgOf = () => JSON.parse(fs.readFileSync(path.join(ROOT, 'build', 'page', 'index.html'), 'utf8').match(/<script id="ls-cfg" type="application\/json">(.*?)<\/script>/s)[1].replace(/<\\\//g, '</'));
const cfg = cfgOf();
const synthetic = !!cfg.cardsSynthetic;
if (!cfg.cards) { console.log('SKIP the built page has no cards (run tools/prep_cards.py first)'); process.exit(0); }
const ids = ['title', 'between', 'ode', 'turca'];
const files = fs.readdirSync(path.join(ROOT, 'build', 'page', 'cards'));
check('build: every card has its video and its poster', ids.every(i => files.includes(i + '.mp4') && files.includes(i + '.jpg')), `${files.length} files in cards/ (${synthetic ? 'test patterns' : 'AI-made'})`);

// ---- 1. the test clock leaves cards out unless they are asked for ------------------------------------------------------------------------------------
{
  const A = await openPage({ manual: true });
  try {
    const n = await A.page.evaluate(() => ({ on: Loomsong.cards.on, cards: document.querySelectorAll('.ls-card').length, videos: document.querySelectorAll('video').length }));
    check('test clock: no card unless cards=on', n.on === false && n.cards === 0 && n.videos === 0, JSON.stringify(n));
    check('test clock: no page errors', A.problems().length === 0, A.problems().slice(0, 2).join(' | ') || 'none');
  } finally { await A.close(); }
}

// ---- 2. the cards, one run through the page -----------------------------------------------------------------------------------------------------------
{
  const A = await openPage({ manual: true, query: 'cards=on' });
  const P = A.page, ev = (fn, arg) => P.evaluate(fn, arg), settle = n => A.frames(n);
  try {
    // title
    await P.waitForFunction(() => Loomsong.cards.status().title && Loomsong.cards.status().title.ready >= 2, null, { timeout: 60000 });
    const T = await ev(() => { const v = document.querySelector('.ls-splash video'); return { src: v && v.getAttribute('src'), poster: v && v.getAttribute('poster'), muted: v && v.muted, controls: v && v.controls, loop: v && v.loop, playsinline: v && v.hasAttribute('playsinline'),
      behind: v && getComputedStyle(v.parentElement).zIndex, pe: v && getComputedStyle(v.parentElement).pointerEvents, st: Loomsong.cards.status().title, splashAi: document.querySelector('.ls-splash-ai').textContent, splashAiHidden: document.querySelector('.ls-splash-ai').hidden }; });
    check('title: a muted looping video behind the title', T.src === 'cards/title.mp4' && /cards\/title\.jpg$/.test(T.poster) && T.muted && !T.controls && T.loop && T.playsinline && T.behind === '-1' && T.pe === 'none', `${T.src}, poster ${T.poster}, muted ${T.muted}, loop ${T.loop}, layer z ${T.behind}, pointer events ${T.pe}`);
    await P.waitForFunction(() => Loomsong.cards.status().title.playing, null, { timeout: 30000 });
    check('title: it plays', true, JSON.stringify(await ev(() => Loomsong.cards.status().title)));
    check('title: the words about it', synthetic ? T.splashAiHidden : (!T.splashAiHidden && /AI-made/.test(T.splashAi)), synthetic ? 'test patterns: no AI claim on the title card' : T.splashAi);

    // play: the clock starts at once, the opening covers the world
    await ev(() => document.querySelector('.ls-big').click());
    const o = await ev(() => ({ playing: Loomsong.clock.playing, hidden: document.querySelector('.ls-card-open').hidden, name: document.querySelector('.ls-card-name').textContent, by: document.querySelector('.ls-card-by').textContent,
      src: (document.querySelector('.ls-card-open video') || {}).getAttribute && document.querySelector('.ls-card-open video').getAttribute('src'), caption: document.querySelector('.ls-card-ai').textContent,
      z: getComputedStyle(document.querySelector('.ls-card-open')).zIndex, splashHidden: document.querySelector('.ls-splash').hidden, status: Loomsong.cards.status().opening }));
    check('opening: the clock does not wait', o.playing === true && o.splashHidden === true, `playing ${o.playing}, title card gone ${o.splashHidden}`);
    check('opening: covers the world with the piece\'s name', o.hidden === false && o.name === 'Ode to Joy' && /Beethoven/.test(o.by) && o.src === 'cards/ode.mp4' && o.status === true, `${o.name} / ${o.by}, ${o.src}`);
    check('opening: it says what it is', synthetic ? /Test pattern/.test(o.caption) : /AI-made/.test(o.caption), o.caption);
    await P.waitForFunction(() => Loomsong.cards.status().open.ode.playing, null, { timeout: 30000 });
    // under the interface, not over it
    const stack = await ev(() => { const z = s => Number(getComputedStyle(document.querySelector(s)).zIndex); return { card: z('.ls-card-open'), corner: z('.ls-corner'), compass: z('.ls-compass'), stage: document.querySelector('#ls-stage').compareDocumentPosition(document.querySelector('.ls-card-open')) & Node.DOCUMENT_POSITION_FOLLOWING ? 'after the stage' : 'before' }; });
    check('opening: under the interface', stack.card < stack.corner && stack.card < stack.compass && stack.stage === 'after the stage', JSON.stringify(stack));
    // it dissolves on its own timer
    await P.waitForFunction(() => document.querySelector('.ls-card-open').hidden === true, null, { timeout: 120000 });
    check('opening: it dissolves into the world', await ev(() => Loomsong.cards.status().opening === false && Loomsong.clock.playing), 'hidden by its own timer; the clock kept going');
    // once only
    await P.keyboard.press('Space'); await settle(2); await P.keyboard.press('Space'); await settle(2);
    check('opening: not again after a pause', await ev(() => document.querySelector('.ls-card-open').hidden === true), 'pause and play at the same piece: no second opening');

    // the other piece, skipped early
    await P.keyboard.press('2');
    await P.waitForFunction(() => Loomsong.piece.id === 'turca' && Loomsong.meta && Loomsong.meta.piece === 'turca' && Loomsong.clock.mode === 'manual', null, { timeout: 180000 });
    await P.waitForFunction(() => !document.querySelector('.ls-card-open').hidden, null, { timeout: 30000 });
    const o2 = await ev(() => ({ name: document.querySelector('.ls-card-name').textContent, src: document.querySelector('.ls-card-open video').getAttribute('src') }));
    check('opening: the second piece has its own', o2.name === 'Rondo alla Turca' && o2.src === 'cards/turca.mp4', `${o2.name}, ${o2.src}`);
    const t0 = Date.now();
    await P.keyboard.press('Escape');
    const asked = await ev(() => Loomsong.cards.skipT > 0 || !Loomsong.cards.cur);          // the skip is registered at once; the dissolve is under half a second of frames
    await P.waitForFunction(() => document.querySelector('.ls-card-open').hidden === true, null, { timeout: 60000 });
    check('opening: Escape ends it early', asked && await ev(() => Loomsong.clock.playing) && (Date.now() - t0) < 30000, `skip registered at once, gone ${((Date.now() - t0) / 1000).toFixed(1)} s after Escape (software frames are slow); the clock kept going`);

    // calm leaves the opening out
    await P.keyboard.press('k'); await settle(2);
    await P.keyboard.press('1');
    await P.waitForFunction(() => Loomsong.piece.id === 'ode' && Loomsong.meta && Loomsong.meta.piece === 'ode' && Loomsong.clock.mode === 'manual', null, { timeout: 180000 });
    await settle(3);
    check('calm: no opening', await ev(() => document.querySelector('.ls-card-open').hidden === true && Loomsong.cards.status().opening === false && Loomsong.calm === true), 'with K on, the piece opens on the world');
    await P.keyboard.press('k'); await settle(2);

    // the end card
    await ev(D => Loomsong.clock.setTime(D), await ev(() => Loomsong.D)); await settle(3);
    await P.waitForFunction(() => Loomsong.cards.status().between.playing, null, { timeout: 60000 });
    const E = await ev(() => { const c = document.querySelector('.ls-credits'), v = c.querySelector('video'); return { show: c.getAttribute('data-show'), card: c.getAttribute('data-card'), src: v && v.getAttribute('src'), loop: v && v.loop, muted: v && v.muted, text: document.querySelector('.ls-credbody').textContent, ai: Loomsong.piece.ai, shared: Loomsong.cfg.pageAi || [] }; });
    check('end card: the in-between picture behind the credits', E.show === '1' && E.card === '1' && E.src === 'cards/between.mp4' && E.loop && E.muted && /Beethoven/.test(E.text), `${E.src}, credits ${E.text.length} characters`);
    check('end card: the AI words match the cards', synthetic ? (E.shared.length === 0 && !/Also AI-made/.test(E.text)) : (E.shared.length === 2 && E.shared.every(s => E.text.includes(s)) && E.ai.some(a => /opening card/.test(a))), synthetic ? 'test patterns are not called AI-made' : `${E.shared.join('; ')}; the piece lists its opening card`);
    await P.keyboard.press('k'); await settle(4);
    check('calm: the looping card holds still', await ev(() => !Loomsong.cards.status().between.playing), 'K pauses the end card\'s video; its poster stays');
    await P.keyboard.press('k');
    const errs = (await ev(() => Loomsong.errors)).filter(e => !/WebAssembly|wasm/i.test(e));
    check('no page errors', errs.length === 0 && A.problems().length === 0, errs.concat(A.problems()).slice(0, 4).join(' | ') || 'none');
    const shot = await P.screenshot({ type: 'png' });
    fs.writeFileSync(path.join(runs, 'cards-endcard.png'), shot);
  } finally { await A.close(); }
}

// ---- 3. the video files do not arrive ------------------------------------------------------------------------------------------------------------------
{
  const A = await openPage({ manual: true, query: 'cards=on', without: /^cards\/.*\.mp4$/ });
  const P = A.page, ev = (fn, arg) => P.evaluate(fn, arg), settle = n => A.frames(n);
  try {
    await P.waitForFunction(() => Loomsong.cards.status().title.error > 0, null, { timeout: 60000 });
    check('missing video: the title still shows its poster', await ev(() => { const v = document.querySelector('.ls-splash video'); return v.getAttribute('poster') && !document.querySelector('.ls-splash').hidden; }), 'the splash and its poster are there; the video says it failed');
    await ev(() => document.querySelector('.ls-big').click()); await settle(2);
    check('missing video: Play still starts the music', await ev(() => Loomsong.clock.playing && !Loomsong.cards.status().open.ode.playing), 'the clock runs with no video to show');
    await P.waitForFunction(() => document.querySelector('.ls-card-open').hidden === true, null, { timeout: 120000 });
    check('missing video: the opening still ends on its timer', true, 'it showed the poster and dissolved');
    const bad = A.problems().filter(p => !/cards\/[a-z]+\.mp4|Failed to load resource|404/i.test(p));
    check('missing video: only the failed requests are reported', bad.length === 0 && A.problems().length > 0, bad.slice(0, 2).join(' | ') || `${A.problems().length} reports, all of the missing videos`);
  } finally { await A.close(); }
}

const ok = checks.length > 0 && checks.every(c => c.ok);
fs.writeFileSync(path.join(runs, 'cards.json'), JSON.stringify({ witness: 'cards', ok, synthetic, checks }, null, 1));
console.log(ok ? `Cards tests green (${checks.length} checks)` : 'Cards tests RED');
process.exitCode = ok ? 0 : 1;
