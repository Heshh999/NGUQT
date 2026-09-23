/* MROF God's Eye View — Mechanism theatre.
   One scripted, synthetic scenario per hypothesis, played beat by beat on
   a canvas while the family's frozen conditions light up. The scripts
   come from the registry (/api/registry: demos + resolved conditions);
   tests_godseye.py::G11 runs the frozen detector on every script's final
   beat, so what plays here is what the code fires on. Nothing here is
   market data, a result or an outcome. */
'use strict';

S.th = { reg: null, err: null, id: 'A1', beat: 0, t: 0, playing: false,
         counter: false, raf: null, last: 0, lab: null, speed: 1 };

const TH_BEAT_MS = 1400;
const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

async function loadRegistry() {
  if (S.th.reg) return S.th.reg;
  try {
    const r = await fetch('/api/registry', { cache: 'no-store' });
    S.th.reg = await r.json(); S.th.err = null;
  } catch (e) { S.th.err = 'registry unavailable: ' + e; }
  render();
  return S.th.reg;
}

// ---------------------------------------------------------------- rules
// the same clause evaluator as godseye_registry._clause, so the
// checklist agrees with the server's explanation of a real window
function evalClause(cl, f) {
  if (cl.op === 'any') {
    const subs = cl.clauses.map(c => evalClause(c, f));
    return { op: 'any', clauses: subs, passed: subs.some(s => s.passed === true) };
  }
  const v = f[cl.feature];
  let passed;
  if (v === null || v === undefined) passed = null;
  else if (cl.op === 'is_true') passed = v === true;
  else if (cl.op === '>=') passed = v >= cl.value;
  else if (cl.op === '<=') passed = v <= cl.value;
  else if (cl.op === '<') passed = v < cl.value;
  else if (cl.op === '!=') passed = v !== cl.value;
  return { feature: cl.feature, op: cl.op, value: cl.value, observed: v, passed };
}
function verdict(res, f) {
  const g = (res.gate || []).map(c => evalClause(c, f));
  const c = (res.conditions || []).map(cl => evalClause(cl, f));
  const missing = (res.required_inputs || []).filter(k => f[k] === null || f[k] === undefined);
  const all = g.every(x => x.passed === true) && !missing.length && c.every(x => x.passed === true);
  return { gate: g, conditions: c, missing, all };
}
function fireDirection(sign, f) {
  if (!sign) return 0;
  const neg = sign.startsWith('-'); const key = sign.replace(/^-/, '');
  const v = f[key]; if (v === null || v === undefined) return 0;
  return neg ? -v : v;
}
function clauseText(c) {
  if (c.op === 'any') return 'any of: ' + c.clauses.map(clauseText).join(' | ');
  return c.feature + ' ' + (c.op === 'is_true' ? 'is true' : c.op + ' ' + c.value);
}

// accumulated inputs up to (and including) beat i; the counter-example
// overrides apply from the final beat on
function inputsAt(demo, i, counter) {
  const f = {};
  demo.beats.slice(0, i + 1).forEach(b => b.inputs.forEach(([k, v]) => { f[k] = v; }));
  if (counter && i >= demo.beats.length - 1) (demo.counter.inputs || []).forEach(([k, v]) => { f[k] = v; });
  return f;
}
function currentDemo() { return (S.th.reg && S.th.reg.demos || []).find(d => d.id === S.th.id) || null; }

// ---------------------------------------------------------------- view
function viewTheatre(snap) {
  const th = S.th; const cards = [];
  if (!th.reg) { loadRegistry(); cards.push(h('section', { class: 'card' }, h('div', { class: 'dim' }, th.err || 'loading the registry…'))); return cards; }
  const fams = (snap.hypotheses || {}).families || [];
  const demo = currentDemo();
  cards.push(h('div', { class: 'banner syn', style: 'grid-column: span 12' }, th.reg.demo_note));
  cards.push(h('section', { class: 'card c3' }, h('h2', null, 'Hypotheses'),
    h('small', null, 'one scripted scenario each; the counter-example changes one thing and does not fire'),
    h('div', { class: 'list', style: 'max-height:none' }, ...th.reg.demos.map(d => {
      const fam = fams.find(f => f.id === d.id) || {};
      return h('div', { class: 'item' + (d.id === th.id ? ' sel' : ''), onclick: () => { th.id = d.id; th.beat = 0; th.t = 0; th.playing = false; th.counter = false; th.lab = null; render(); } },
        h('div', null, h('code', null, d.id), ' ', d.title), h('small', null, chip(fam.implementation === 'IMPLEMENTED' ? 'READY' : fam.implementation === 'CONTROL' ? 'CONTROL' : 'NOT_WIRED', fam.implementation || '—'), ' ', fam.status ? chip(fam.status) : null));
    }))));
  if (!demo) { cards.push(h('section', { class: 'card c9' }, h('div', { class: 'dim' }, 'no script for ' + th.id))); return cards; }
  const res = th.reg.resolved[demo.id] || { gate: [], conditions: [], required_inputs: [] };
  const hyp = th.reg.hypotheses.find(x => x.id === demo.id) || {};
  const n = demo.beats.length; const last = th.beat >= n - 1;
  const f = th.lab || inputsAt(demo, th.beat, th.counter);
  // candle arms have no clause list: their verdict is the frozen arm rule's
  // (tests G11c run arm_b1/arm_b2 on these very bars); the textbook bars
  // fire -ad, the counter-example's bars do not
  const v = demo.kind === 'candles'
    ? { gate: [], conditions: [], missing: [], all: last && !th.counter, rule: hyp.mechanism }
    : verdict(res, f);
  const dir = v.all ? (demo.kind === 'candles' ? -demo.ad : fireDirection(res.direction_sign, f)) : 0;
  const beat = demo.beats[Math.min(th.beat, n - 1)];
  const caption = (th.counter && last) ? demo.counter.caption : beat.caption;
  // stage
  const cv = h('canvas', { width: 900, height: 380, id: 'stage' });
  const mid = h('section', { class: 'card c6' },
    h('div', { class: 'row' }, h('h2', null, `${demo.id} · ${demo.title}`), chip(hyp.wave === 2 ? 'CONTROL' : 'READY', 'wave ' + hyp.wave), th.counter ? chip('INVALID_OR_MISSING_DATA', 'COUNTER-EXAMPLE') : chip('EXPOSED', 'TEXTBOOK')),
    h('p', { class: 'dim', style: 'margin:0 0 8px' }, demo.setting),
    cv,
    h('div', { class: 'caption' }, h('span', { class: 'mono dim' }, `beat ${Math.min(th.beat + 1, n)}/${n}  `), caption),
    h('div', { class: 'controls' },
      h('button', { onclick: () => { th.playing = !th.playing; if (th.playing && last) { th.beat = 0; th.t = 0; } thTick(); render(); } }, th.playing ? '⏸ pause' : '▶ play'),
      h('button', { onclick: () => { th.playing = false; th.beat = 0; th.t = 0; render(); } }, '⏮ restart'),
      h('button', { onclick: () => thStep(-1) }, '◀ beat'), h('button', { onclick: () => thStep(1) }, 'beat ▶'),
      h('button', { class: th.counter ? 'on' : '', onclick: () => { th.counter = !th.counter; th.lab = null; th.beat = n - 1; th.t = 1; th.playing = false; render(); } }, th.counter ? 'counter-example ON' : 'show the counter-example'),
      h('label', { class: 'dim' }, 'speed ', h('select', { onchange: (e) => { th.speed = +e.target.value; } }, ...[0.5, 1, 2].map(s => h('option', { value: s, selected: s === th.speed ? 'selected' : null }, s + '×')))),
      h('span', { class: 'dim' }, 'keys: space · ← → · c')),
    h('div', { class: 'verdict ' + (last ? (v.all ? 'fire' : 'nofire') : '') },
      !last ? 'conditions are still being observed…' :
      v.all ? `every condition held → the frozen rule fires ${dir > 0 ? '▲ LONG' : dir < 0 ? '▼ SHORT' : ''} (${hyp.direction_rule || ''})` :
      demo.kind === 'candles' ? 'no fire: the candle rule is not met (' + demo.counter.caption + ')' :
      `no fire: ${v.missing.length ? 'inputs missing: ' + v.missing.join(', ') : 'a condition failed: ' + [...v.gate, ...v.conditions].filter(c => c.passed !== true).map(clauseText).join('; ')}`),
    h('small', null, 'a research event, not a trade: no fill, stop, target or outcome exists anywhere in this project'));
  // right: checklist + thought experiment
  const right = h('section', { class: 'card c3' }, h('h2', null, 'Frozen conditions'),
    res.forced_none && res.forced_none.length ? h('small', null, 'forced None in this family: ' + res.forced_none.join(', ')) : null,
    demo.kind === 'candles' ? h('ul', { class: 'cond' }, h('li', null, hyp.mechanism), h('li', null, 'direction: ' + hyp.direction_rule))
                            : h('ul', { class: 'cond' }, ...v.gate.map(c => condLine(c, 'gate')), ...v.conditions.map(c => condLine(c))),
    v.missing.length ? h('div', { class: 'dim' }, 'not yet observed: ' + v.missing.join(', ')) : null,
    demo.kind === 'candles' ? h('div', { class: 'notice' }, 'a candle-only control: no flow input; the bars are the whole input, and the frozen arm function is what tests_godseye G11c runs on them') : thoughtExperiment(demo, res, hyp, f));
  cards.push(mid, right);
  setTimeout(() => drawStage(cv, demo, res, hyp, f, v, dir), 0);
  return cards;
}

// sliders on the family's inputs; the checklist re-evaluates live. This
// mirrors the written conditions (pinned to the code by G1b/G11); it
// does not call the frozen function and it touches no data
function thoughtExperiment(demo, res, hyp, f) {
  const th = S.th;
  const base = inputsAt(demo, demo.beats.length - 1, th.counter);
  const names = Object.keys(base);
  const rangeFor = (k, val) => {
    if (typeof val === 'boolean') return null;
    if (/_z$|_z_hc$/.test(k)) return [0, 4, 0.1];
    if (/frac|ratio/.test(k)) return [0, 1.5, 0.05];
    if (/ticks|approaches|persist/.test(k)) return [0, 6, 1];
    if (/_dir$/.test(k)) return [-1, 1, 2];
    return [0, 4, 0.1];
  };
  const box = h('div', null, h('h3', null, 'thought experiment'),
    h('small', null, 'move an input; the checklist follows the written conditions. Reset returns to the script.'));
  for (const k of names) {
    const val = th.lab ? th.lab[k] : base[k];
    const rg = rangeFor(k, base[k]);
    const row = h('div', { class: 'lab' }, h('code', null, k));
    if (rg === null) {
      row.append(h('button', { class: val ? 'on' : '', onclick: () => { th.lab = Object.assign({}, th.lab || base, { [k]: !val }); th.beat = demo.beats.length - 1; th.t = 1; th.playing = false; render(); } }, val ? 'true' : 'false'));
    } else {
      row.append(h('input', { type: 'range', min: rg[0], max: rg[1], step: rg[2], value: val, oninput: (e) => { th.lab = Object.assign({}, th.lab || base, { [k]: +e.target.value }); th.beat = demo.beats.length - 1; th.t = 1; th.playing = false; render(); } }),
                 h('span', { class: 'mono' }, String(val)));
    }
    box.append(row);
  }
  box.append(h('button', { onclick: () => { th.lab = null; render(); } }, 'reset to the script'));
  return box;
}

// ---------------------------------------------------------------- animation
function thStep(d) {
  const th = S.th; const demo = currentDemo(); if (!demo) return;
  th.playing = false; th.beat = Math.max(0, Math.min(demo.beats.length - 1, th.beat + d)); th.t = 1; render();
}
function thTick(now) {
  const th = S.th; if (!th.playing) return;
  const demo = currentDemo(); if (!demo) { th.playing = false; return; }
  if (REDUCED) { th.t = 1; if (th.beat < demo.beats.length - 1) { th.beat++; setTimeout(() => { render(); thTick(); }, TH_BEAT_MS / th.speed); } else { th.playing = false; render(); } return; }
  if (now === undefined) { th.last = performance.now(); th.raf = requestAnimationFrame(thTick); return; }
  const dt = (now - th.last) * th.speed; th.last = now;
  th.t += dt / TH_BEAT_MS;
  if (th.t >= 1) {
    if (th.beat >= demo.beats.length - 1) { th.t = 1; th.playing = false; render(); return; }
    th.beat++; th.t = 0; render();
  } else {
    const cv = document.getElementById('stage');
    if (cv) { const res = th.reg.resolved[demo.id] || {}; const hyp = th.reg.hypotheses.find(x => x.id === demo.id) || {};
      const f = inputsAt(demo, th.beat, th.counter); const v = verdict(res, f); drawStage(cv, demo, res, hyp, f, v, v.all ? fireDirection(res.direction_sign, f) : 0); }
  }
  th.raf = requestAnimationFrame(thTick);
}

// ---------------------------------------------------------------- stage
const TICK_PX = 24;
function drawStage(cv, demo, res, hyp, f, v, dir) {
  const ctx = cv.getContext('2d'); const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#0f1216'; ctx.fillRect(0, 0, W, H);
  ctx.font = '12px monospace';
  if (demo.kind === 'candles') return drawCandleStage(ctx, W, H, demo, v, dir);
  const th = S.th; const n = demo.beats.length; const last = th.beat >= n - 1;
  const left = 60, right = W - 150, top = 30, bottom = H - 40;
  const X = (b) => left + (right - left) * (b / Math.max(n - 1, 1));
  const midY = (top + bottom) / 2; const Y = (px) => midY - px * TICK_PX;
  // tick grid
  ctx.strokeStyle = '#1c2229'; for (let k = -6; k <= 6; k++) { ctx.beginPath(); ctx.moveTo(left, Y(k)); ctx.lineTo(right, Y(k)); ctx.stroke(); }
  ctx.fillStyle = '#66717c'; for (let k = -6; k <= 6; k += 2) ctx.fillText((k > 0 ? '+' : '') + k + 't', 8, Y(k) + 4);
  // beat columns
  for (let b = 0; b < n; b++) { ctx.strokeStyle = b <= th.beat ? '#2a323b' : '#1c2229'; ctx.beginPath(); ctx.moveTo(X(b), top); ctx.lineTo(X(b), bottom); ctx.stroke(); ctx.fillStyle = b <= th.beat ? '#98a3ae' : '#3a434c'; ctx.fillText('beat ' + (b + 1), X(b) - 20, bottom + 16); }
  // level
  ctx.strokeStyle = '#e0b341'; ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(left, Y(0)); ctx.lineTo(right, Y(0)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#e0b341'; ctx.fillText(demo.level + (demo.ad > 0 ? '  (approached from below)' : '  (approached from above)'), left + 4, Y(0) - 6);
  // price path up to the current progress
  const prog = Math.min(th.beat + (last ? 1 : th.t), n - 1);
  const pxAt = (b) => { const i = Math.floor(b), j = Math.min(i + 1, n - 1); const t = b - i; return demo.beats[i].px + (demo.beats[j].px - demo.beats[i].px) * t; };
  ctx.strokeStyle = '#d9dee4'; ctx.lineWidth = 2; ctx.beginPath();
  for (let b = 0; b <= prog + 1e-9; b += 0.05) { const bb = Math.min(b, prog); const x = X(bb), y = Y(pxAt(bb)); b === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
  ctx.lineTo(X(prog), Y(pxAt(prog))); ctx.stroke(); ctx.lineWidth = 1;
  ctx.fillStyle = '#6fb1ff'; ctx.beginPath(); ctx.arc(X(prog), Y(pxAt(prog)), 5, 0, 6.28); ctx.fill();
  // prints per beat (executions), placed on the price of that beat
  for (let b = 0; b <= th.beat; b++) {
    const bt = demo.beats[b]; const shown = b < th.beat || last ? bt.prints.length : Math.floor(bt.prints.length * th.t);
    bt.prints.slice(0, shown).forEach((p, i) => { const x = X(b) + 10 + i * 14, y = Y(bt.px) + (p[0] === 'BUY' ? 12 : -12); ctx.fillStyle = p[0] === 'BUY' ? '#3fbf7f' : '#e06c5d'; ctx.beginPath(); ctx.arc(x, y, Math.min(8, 2 + Math.sqrt(p[1])), 0, 6.28); ctx.fill(); });
  }
  // resting size at the level (displayed): ask above, bid below
  const bx = right + 20; const cur = demo.beats[Math.min(th.beat, n - 1)]; const prev = demo.beats[Math.max(th.beat - 1, 0)];
  const lerp = (a, b) => a + (b - a) * (last ? 1 : th.t);
  const ask = lerp(prev.ask, cur.ask), bid = lerp(prev.bid, cur.bid); const sc = 1.6;
  ctx.fillStyle = '#e06c5d'; ctx.fillRect(bx, Y(0) - 4 - ask * sc, 36, ask * sc);
  ctx.fillStyle = '#3fbf7f'; ctx.fillRect(bx, Y(0) + 4, 36, bid * sc);
  ctx.fillStyle = '#98a3ae'; ctx.fillText('resting at the level', bx - 10, top + 6); ctx.fillText('ask ' + Math.round(ask), bx + 42, Y(0) - 8); ctx.fillText('bid ' + Math.round(bid), bx + 42, Y(0) + 16);
  ctx.fillText('(displayed size,', bx - 10, bottom - 14); ctx.fillText(' not executed)', bx - 10, bottom - 2);
  // verdict marker
  if (last) {
    const x = X(n - 1), y = Y(demo.beats[n - 1].px);
    if (v.all && dir) { ctx.fillStyle = dir > 0 ? '#3fbf7f' : '#e06c5d'; ctx.beginPath(); if (dir > 0) { ctx.moveTo(x, y - 34); ctx.lineTo(x - 10, y - 16); ctx.lineTo(x + 10, y - 16); } else { ctx.moveTo(x, y + 34); ctx.lineTo(x - 10, y + 16); ctx.lineTo(x + 10, y + 16); } ctx.fill(); ctx.fillText(dir > 0 ? 'FIRE LONG' : 'FIRE SHORT', x - 32, dir > 0 ? y - 40 : y + 48); }
    else { ctx.fillStyle = '#98a3ae'; ctx.fillText('NO FIRE', x - 20, y - 20); }
  }
  ctx.fillStyle = '#66717c'; ctx.fillText('scripted illustration · price in ticks from the level · dots are executions (green buy / red sell)', left, 16);
}
function drawCandleStage(ctx, W, H, demo, v, dir) {
  const th = S.th; const bars = th.counter ? demo.counter.bars : demo.bars; const lp = demo.level_px;
  const lo = Math.min(...bars.map(b => b[3])) - 1, hi = Math.max(...bars.map(b => b[2])) + 1;
  const top = 30, bottom = H - 40; const Y = (p) => top + (bottom - top) * (1 - (p - lo) / (hi - lo));
  ctx.strokeStyle = '#e0b341'; ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(60, Y(lp)); ctx.lineTo(W - 60, Y(lp)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#e0b341'; ctx.fillText(demo.level + ' @ ' + lp.toFixed(2), 64, Y(lp) - 6);
  bars.forEach((b, i) => {
    const [, o, hh, ll, c] = b; const x = 200 + i * 220; const up = c >= o; const col = up ? '#3fbf7f' : '#e06c5d';
    const revealed = i <= Math.max(0, th.beat - (demo.id === 'ARM-B2' ? 1 : 0)) || th.beat >= demo.beats.length - 1;
    ctx.globalAlpha = revealed ? 1 : 0.25;
    ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, Y(hh)); ctx.lineTo(x, Y(ll)); ctx.stroke();
    ctx.fillStyle = col; ctx.fillRect(x - 22, Y(Math.max(o, c)), 44, Math.max(2, Math.abs(Y(o) - Y(c))));
    ctx.lineWidth = 1; ctx.globalAlpha = 1;
    ctx.fillStyle = '#98a3ae'; ctx.fillText(`bar ${i + 1}: o ${o} h ${hh} l ${ll} c ${c}`, x - 60, bottom + 16);
    // the wick beyond the level, highlighted when the script talks about it
    if (demo.id === 'ARM-B1' && th.beat >= 1) { ctx.strokeStyle = '#6fb1ff'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x + 30, Y(hh)); ctx.lineTo(x + 30, Y(lp)); ctx.stroke(); ctx.lineWidth = 1; ctx.fillStyle = '#6fb1ff'; ctx.fillText('wick beyond the level', x + 36, (Y(hh) + Y(lp)) / 2); }
  });
  const last = th.beat >= demo.beats.length - 1;
  if (last) { ctx.fillStyle = v.all || (!th.counter) ? (dir < 0 ? '#e06c5d' : '#3fbf7f') : '#98a3ae';
    const fires = th.counter ? 0 : (demo.ad > 0 ? -1 : 1);
    ctx.fillStyle = fires ? (fires < 0 ? '#e06c5d' : '#3fbf7f') : '#98a3ae';
    ctx.font = 'bold 14px monospace'; ctx.fillText(fires ? (fires < 0 ? '▼ FIRE SHORT (-ad)' : '▲ FIRE LONG (-ad)') : 'NO FIRE', W - 260, 60); ctx.font = '12px monospace'; }
  ctx.fillStyle = '#66717c'; ctx.fillText('scripted illustration · 1-minute bars · a candle-only control arm, no flow input', 60, 16);
}

document.addEventListener('keydown', (e) => {
  const tag = (e.target || {}).tagName;
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(tag)) return;
  if (tag === 'BUTTON' && e.key === ' ') return;   // space on a focused button is that button's click
  if (e.key >= '1' && e.key <= '5') { const v = ['health', 'hyp', 'theatre', 'prov', 'replay'][+e.key - 1]; if (v) setView(v); return; }
  if (S.view === 'theatre') {
    if (e.key === ' ') { e.preventDefault(); const th = S.th; th.playing = !th.playing; if (th.playing && th.beat >= (currentDemo() || { beats: [] }).beats.length - 1) { th.beat = 0; th.t = 0; } thTick(); render(); }
    else if (e.key === 'ArrowLeft') thStep(-1); else if (e.key === 'ArrowRight') thStep(1);
    else if (e.key === 'c') { const th = S.th; th.counter = !th.counter; th.lab = null; th.beat = (currentDemo() || { beats: [] }).beats.length - 1; th.t = 1; th.playing = false; render(); }
  } else if (S.view === 'replay' && S.rp.bundle) {
    if (e.key === ' ') { e.preventDefault(); S.rp.playing = !S.rp.playing; tick(); }
    else if (e.key === 'ArrowLeft') step(-1); else if (e.key === 'ArrowRight') step(1);
  }
});
