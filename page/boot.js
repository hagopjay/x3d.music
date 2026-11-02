/* Loomsong boot: read the config, build the app and its interface, open the first piece. The page wants #ode or #turca in the address for the first piece. */
(function (global) {
  'use strict';
  var d = global.document;
  var cfg = JSON.parse(d.getElementById('ls-cfg').textContent);
  var root = d.getElementById('ls-root'), host = d.getElementById('ls-stage');
  var app = new global.LoomApp(cfg);
  global.Loomsong = app;
  var ui = new global.LoomUI(app, root);
  app.ui = ui;
  if (global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches) app.calm = true;     // calm mode by default for people who ask for less motion
  var want = (global.location.hash || '').replace('#', '');
  var first = cfg.pieces.some(function (p) { return p.id === want; }) ? want : cfg.pieces[0].id;
  app.start(host, first).catch(function (e) { ui.splashNote.textContent = 'Could not load: ' + e; global.console.error(String(e)); });
})(window);
