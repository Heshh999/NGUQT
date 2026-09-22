/* MROF God's Eye View — frontend. Vanilla JS, no build step, no CDN.
   Renders the exporter's snapshot; asks the server for replay bundles
   of EXPOSED sessions only. It never computes research statistics: every
   count on screen is quoted from a released report, every status from
   the exporter, every replay row from a bounded server read. */
'use strict';

const S = {
  view: 'health', data: null, err: null, lastOk: null,
  sel: { hyp: null, session: null, run: null },
  rp: { session: null, instrument: 'NQ', windows: null, winErr: null,
        approach: null, window: null, bundle: null, bErr: null, cursor: 0,
        playing: false, timer: null, explain: null },
};
const ET = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York',
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit',
  minute: '2-digit', second: '2-digit', hour12: false });
const ETs = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

// ---------------------------------------------------------------- utils
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) e.setAttribute(k, v);
  }
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    e.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
  return e;
}
const txt = (s) => document.createTextNode(s);
function toEpoch(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number') return v;
  const t = Date.parse(v.replace(' ', 'T').replace(/\+00:00$/, 'Z'));
  return isNaN(t) ? null : t / 1000;
}
function fmtET(v) {
  const e = toEpoch(v); if (e === null) return '—';
  return ET.format(new Date(e * 1000)).replace(',', '') + ' ET';
}
function fmtETt(v) {
  const e = toEpoch(v); if (e === null) return '—';
  return ETs.format(new Date(e * 1000));
}
function fmtUTC(v) {
  const e = toEpoch(v); if (e === null) return '—';
  return new Date(e * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z');
}
function ago(sec) {
  if (sec === null || sec === undefined) return '—';
  if (sec < 90) return Math.round(sec) + ' s';
  if (sec < 5400) return Math.round(sec / 60) + ' min';
  if (sec < 172800) return (sec / 3600).toFixed(1) + ' h';
  return (sec / 86400).toFixed(1) + ' d';
}
function bytes(n) {
  if (n === null || n === undefined) return '—';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; let x = n;
  while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
  return (i ? x.toFixed(x < 10 ? 2 : 1) : x) + ' ' + u[i];
}
const pct = (f) => (f === null || f === undefined) ? '—' : (100 * f).toFixed(1) + '%';
// prices are shown to the tick (0.25); the runner's own floats are never altered, only displayed
const fpx = (v) => (typeof v === 'number' && Number.isFinite(v)) ? v.toFixed(2) : (v === null || v === undefined ? '—' : String(v));
const n0 = (v) => (v === null || v === undefined) ? '—' : v;
function pill(status, label) {
  return h('span', { class: 'pill s-' + status }, h('i', { class: 'dot' }),
           txt(label || status));
}
const chip = (s, label) => h('span', { class: 'chip ' + s }, label || s);
function kv(pairs) {
  const g = h('div', { class: 'kv' });
  for (const [k, v] of pairs) {
    g.append(h('div', null, k), h('div', null, v === undefined || v === null ? '—' : v));
  }
  return g;
}
function table(cols, rows, opts) {
  const t = h('table', null,
    h('thead', null, h('tr', null, ...cols.map(c => h('th', { class: c.num ? 'num' : '' }, c.label)))),
    h('tbody', null, ...rows.map(r => {
      const tr = h('tr', { class: (opts && opts.onclick ? 'click ' : '') + (opts && opts.sel && opts.sel(r) ? 'sel' : '') },
        ...cols.map(c => h('td', { class: c.num ? 'num' : '' }, c.get(r))));
      if (opts && opts.onclick) tr.addEventListener('click', () => opts.onclick(r));
      return tr;
    })));
  return h('div', { class: 'scroll' }, t);
}

// ---------------------------------------------------------------- data
async function load() {
  try {
    const r = await fetch('/api/snapshot', { cache: 'no-store' });
    const d = await r.json();
    S.data = d; S.err = null; if (d.snapshot) S.lastOk = d;
  } catch (e) {
    S.err = 'server unreachable: ' + e;
  }
  render();
}

// ---------------------------------------------------------------- header
function renderStrip() {
  const strip = document.getElementById('strip'); strip.innerHTML = '';
  const d = S.data; const snap = d && d.snapshot;
  if (!snap) { strip.append(pill('UNAVAILABLE', 'no snapshot')); return; }
  const hl = snap.health || {};
  strip.append(pill(hl.status || 'UNKNOWN', 'recording: ' + (hl.status || 'UNKNOWN')));
  for (const i of ['NQ', 'MNQ']) {
    const x = (hl.instruments || {})[i] || {};
    const o = x.open_run || {};
    strip.append(pill(x.status || 'UNKNOWN', i + ' ' + (x.status || 'UNKNOWN') +
      (o.newest_row_age_s !== undefined && o.newest_row_age_s !== null ? ' · row ' + ago(o.newest_row_age_s) + ' ago' : '')));
  }
  strip.append(h('span', { class: 'dim' }, 'snapshot ' + ago(d.age_s) + ' old' +
    (d.stale ? ' · STALE' : '')));
  const p = snap.policy || {};
  strip.append(h('span', { class: 'dim' }, 'blind from ' + p.blind_from +
    ' · exposed ' + (p.exposed_sessions || []).length + ' · ledger ' +
    (p.exposure_ledger_error ? 'UNREADABLE' : p.exposure_ledger_days + ' days')));
  if (snap.synthetic) strip.append(chip('BLIND', 'SYNTHETIC DEMO'));
}
function renderBanners() {
  const b = document.getElementById('banners'); b.innerHTML = '';
  const d = S.data;
  if (S.err) b.append(h('div', { class: 'banner err' }, S.err));
  if (!d) return;
  if (d.snapshot && d.snapshot.synthetic)
    b.append(h('div', { class: 'banner syn' }, d.snapshot.synthetic_label));
  if (!d.snapshot) b.append(h('div', { class: 'banner unav' },
    'UNAVAILABLE — ' + (d.snapshot_error || 'no snapshot') + '. Nothing below is a result.'));
  else if (d.stale) b.append(h('div', { class: 'banner stale' },
    'STALE — showing the last successful snapshot (' + d.snapshot.generated_utc +
    '). ' + (d.stale_reason || '')));
  const st = d.status || {};
  if (st.ok === false) b.append(h('div', { class: 'banner err' },
    'Last export FAILED at ' + st.finished_utc + ': ' + st.error));
  const hl = d.snapshot && d.snapshot.health;
  if (hl && !hl.readable) b.append(h('div', { class: 'banner unav' },
    'Capture folder UNAVAILABLE: ' + hl.error));
  if (d.snapshot && (d.snapshot.policy || {}).exposure_ledger_error)
    b.append(h('div', { class: 'banner unav' }, 'Exposure ledger unreadable — every session is UNKNOWN; event-level views are closed. ' +
      d.snapshot.policy.exposure_ledger_error));
}
function renderFooter() {
  const f = document.getElementById('ftr'); f.innerHTML = '';
  const d = S.data; if (!d || !d.snapshot) return;
  const s = d.snapshot;
  f.append(txt(`${s.exporter} · snapshot ${s.generated_utc} · read ${bytes((s.resource_use||{}).bytes_read)} in ${(d.status||{}).duration_s} s · peak heap ${(d.status||{}).peak_python_heap_mb} MB · server ${d.server} · outcome lock file ${s.outcome_lock && s.outcome_lock.exists ? 'PRESENT' : 'absent (outcomes locked)'}`));
}

// ---------------------------------------------------------------- alerts
function alerts(snap) {
  const out = [];
  const hl = snap.health || {};
  if (!hl.readable) out.push(['crit', 'capture folder cannot be read']);
  for (const i of ['NQ', 'MNQ']) {
    const x = (hl.instruments || {})[i] || {};
    if (['DISCONNECTED', 'UNAVAILABLE'].includes(x.status)) out.push(['crit', `${i}: ${x.status} — ${(x.evidence||[])[0]||''}`]);
    else if (x.status === 'STALE') out.push(['warn', `${i}: STALE — ${(x.evidence||[]).slice(-1)[0]||''}`]);
    else if (x.status === 'UNKNOWN') out.push(['warn', `${i}: UNKNOWN — ${(x.evidence||[])[0]||''}`]);
    const hb = (x.open_run || {}).heartbeat || {};
    if (+hb.write_errors > 0) out.push(['crit', `${i}: recorder reports ${hb.write_errors} write error(s)`]);
    if (+hb.dropped > 0) out.push(['warn', `${i}: recorder reports ${hb.dropped} dropped row(s)`]);
  }
  const disk = hl.disk || {};
  if (disk.free_frac !== undefined && disk.free_frac !== null && disk.free_frac < 0.1)
    out.push(['crit', `disk free ${pct(disk.free_frac)} (${bytes(disk.free_bytes)})`]);
  else if (disk.free_bytes !== undefined && disk.free_bytes < 60e9)
    out.push(['warn', `disk free ${bytes(disk.free_bytes)} — under ~3 session-days`]);
  const a = snap.audit || {};
  if (a.ok === false) out.push(['warn', `audit: ${Object.entries(a.failures_by_code||{}).map(([k,v])=>k+'×'+v).join(', ')}`]);
  if (a.ok === null || a.ok === undefined) out.push(['info', 'no audit report loaded']);
  const rv = snap.recovery || {};
  if (rv.orphan_runs) out.push(['warn', `${rv.orphan_runs} orphaned run(s) without a manifest (recover on a weekend)`]);
  const rep = (a.repair_evidence || {}).repaired || {};
  if (rep.verdict === 'NOT_EXERCISED') out.push(['info', 'disconnect repair (1.2.2) not yet exercised: no repaired-build run has had a feed disconnect']);
  if (rep.verdict === 'FAILED') out.push(['crit', 'disconnect repair FAILED on a repaired build']);
  for (const s of (snap.sessions || [])) if (s.shared_gap_s > 300)
    out.push(['warn', `${s.session}: ${ago(s.shared_gap_s)} missing in BOTH instruments (pair overlap ${pct(s.pair_overlap_frac)} cannot see it)`]);
  for (const [k, r] of Object.entries(snap.reports || {})) if (!r.ok) out.push(['info', `${k} report: ${r.error}`]);
  return out;
}

// ---------------------------------------------------------------- views
function viewHealth(snap) {
  const hl = snap.health || {};
  const cards = [];
  const al = alerts(snap);
  cards.push(h('section', { class: 'card' }, h('h2', null, 'Alerts'),
    al.length ? h('ul', { class: 'alerts' }, ...al.map(([l, m]) => h('li', null, h('span', { class: 'lvl ' + l }, l), m)))
              : h('div', { class: 'dim' }, 'nothing needs attention')));
  for (const i of ['NQ', 'MNQ']) {
    const x = (hl.instruments || {})[i] || {}; const o = x.open_run; const c = x.last_closed_run;
    cards.push(h('section', { class: 'card c6' },
      h('div', { class: 'row' }, h('h2', null, i), pill(x.status || 'UNKNOWN'), h('small', null, x.certainty || '')),
      h('ul', null, ...(x.evidence || []).map(e => h('li', { class: 'dim' }, e))),
      o ? [h('h3', null, 'open run (held by the recorder)'), kv([
        ['run', h('code', null, o.run_id)], ['session', o.session], ['contract', o.contract],
        ['build', o.build], ['segment', o.seg], ['newest row', fmtET(o.newest_row_utc) + ' (' + ago(o.newest_row_age_s) + ' ago)'],
        ['UTC', fmtUTC(o.newest_row_utc)],
        ['book ready', o.heartbeat ? (o.heartbeat.book_ready ? 'yes' : 'NO') : '—'],
        ['heartbeat', o.heartbeat ? fmtET(o.heartbeat.utc) : '—'],
        ['write errors', o.heartbeat ? o.heartbeat.write_errors : '—'],
        ['dropped rows', o.heartbeat ? o.heartbeat.dropped : '—'],
        ['queue overflows', o.heartbeat ? o.heartbeat.overflows : '—'],
        ['size so far', bytes(o.bytes_total)]]),
        (o.last_connection_events || []).length ? h('div', null, h('h3', null, 'last connection / book events'),
          h('ul', null, ...o.last_connection_events.map(e => h('li', { class: 'mono' }, `${fmtETt(e.utc)}  ${e.kind}  ${e.detail}`)))) : null]
        : h('div', { class: 'notice' }, 'no run is currently held open by the recorder for ' + i),
      c ? [h('h3', null, 'last closed run'), kv([['run', h('code', null, c.run_id)], ['session', c.session],
        ['contract', c.contract], ['build', c.build], ['closed', c.close_reason], ['last row', fmtET(c.last_recv_utc)], ['manifest', c.source]])] : null));
  }
  const disk = hl.disk || {}; const files = hl.files || {};
  cards.push(h('section', { class: 'card c4' }, h('h2', null, 'Capture folder'),
    kv([['path', h('code', null, hl.path)], ['readable', hl.readable ? 'yes' : 'NO'],
        ['scanned', fmtET(hl.scanned_utc)], ['market', hl.market_scheduled_open ? 'scheduled open' : 'scheduled closed'],
        ['disk free', disk.free_bytes !== undefined ? `${bytes(disk.free_bytes)} of ${bytes(disk.total_bytes)} (${pct(disk.free_frac)})` : (disk.error || '—')]]),
    disk.free_frac !== undefined ? h('div', { class: 'bar', title: 'used' }, h('i', { style: 'width:' + (100 * (1 - disk.free_frac)).toFixed(1) + '%' })) : null,
    h('h3', null, 'files'),
    kv([['manifests', n0(files.manifest)], ['reconstructed manifests', n0(files.reconstructed_manifest)],
        ['finalized csv', n0(files.csv)], ['.partial (open or orphaned)', n0(files.partial)],
        ['recovered copies', n0(files.recovered_csv)], ['total', bytes(files.total_bytes)],
        ['newest file write', fmtET(files.newest_mtime_utc)]]),
    h('small', null, 'liveness decided by: ' + ((hl.liveness_by || []).join(', ') || '—'))));
  // coverage by session
  const ses = (snap.sessions || []).slice().sort((a, b) => b.session < a.session ? -1 : 1);
  cards.push(h('section', { class: 'card c8' }, h('h2', null, 'Expected vs observed coverage'),
    h('div', { class: 'legend' }, h('span', null, h('i', { style: 'background:var(--nq)' }), 'NQ'), h('span', null, h('i', { style: 'background:var(--mnq)' }), 'MNQ'),
      h('span', null, h('i', { class: 'seg gap', style: 'position:static' }), 'gap in one'), h('span', null, h('i', { style: 'background:var(--shared)' }), 'gap in BOTH'),
      h('span', { class: 'dim' }, 'expected: 18:00 ET day before → 17:00 ET; a pair overlap of 1.000 cannot see a shared gap')),
    table([
      { label: 'session', get: r => h('a', { href: '#', onclick: (e) => { e.preventDefault(); S.sel.session = r.session; setView('prov'); } }, r.session) },
      { label: 'class', get: r => chip(r.session_class) },
      { label: 'NQ', get: r => track(r, 'NQ') }, { label: 'NQ %', num: true, get: r => pct(r.instruments.NQ.covered_frac) },
      { label: 'MNQ', get: r => track(r, 'MNQ') }, { label: 'MNQ %', num: true, get: r => pct(r.instruments.MNQ.covered_frac) },
      { label: 'shared gap', num: true, get: r => r.shared_gap_s ? ago(r.shared_gap_s) : '—' },
      { label: 'pair overlap', num: true, get: r => r.pair_overlap_frac === null ? '—' : r.pair_overlap_frac.toFixed(3) },
    ], ses)));
  // audit
  const a = snap.audit || {}; const rep = (a.repair_evidence || {});
  cards.push(h('section', { class: 'card c6' }, h('h2', null, 'Audit'),
    kv([['report', a.source && a.source.path ? h('code', null, a.source.path) : (a.source || {}).error || '—'],
        ['generated', a.source ? fmtET(a.source.mtime_utc) : '—'], ['ok', a.ok === null || a.ok === undefined ? '—' : (a.ok ? 'yes' : 'NO')],
        ['open runs (not failures)', Object.keys(a.open_runs_in_progress || {}).length],
        ['kept originals (not failures)', n0(a.recovery_originals_kept)]]),
    Object.keys(a.failures_by_code || {}).length ? table([{ label: 'failure code', get: r => h('code', null, r[0]) }, { label: 'count', num: true, get: r => r[1] }],
      Object.entries(a.failures_by_code).sort((x, y) => y[1] - x[1])) : h('div', { class: 'dim' }, 'no failures'),
    rep.repaired ? h('div', null, h('h3', null, 'disconnect repair (recorder ≥ 1.2.2)'),
      h('div', { class: 'row' }, chip(rep.repaired.verdict === 'EXERCISED_AND_HELD' ? 'READY' : rep.repaired.verdict === 'FAILED' ? 'INVALID_OR_MISSING_DATA' : 'INSUFFICIENT_PRIOR_HISTORY', rep.repaired.verdict),
        h('small', null, `${rep.repaired.read} of ${rep.repaired.runs} runs read · ${rep.repaired.runs_with_disconnect} with a feed disconnect · ${rep.repaired.spurious_book_ready} spurious BOOK_READY`)),
      table([{ label: 'build', get: r => r[0] }, { label: 'runs', num: true, get: r => r[1].runs }, { label: 'read', num: true, get: r => r[1].read },
             { label: 'disconnects', num: true, get: r => r[1].disconnects }, { label: 'spurious ready', num: true, get: r => r[1].spurious_book_ready }],
        Object.entries(rep.by_build || {}))) : null));
  const rv = snap.recovery || {};
  cards.push(h('section', { class: 'card c6' }, h('h2', null, 'Runs without a manifest'),
    kv([['report', rv.source && rv.source.path ? h('code', null, rv.source.path) : (rv.source || {}).error || '—'],
        ['orphaned (recoverable)', n0(rv.orphan_runs)], ['still being written', n0(rv.live_runs)], ['decided by', (rv.liveness_by || []).join(', ') || '—']]),
    (hl.runs_without_manifest || []).length ? table([
      { label: 'instrument', get: r => chip(r.instrument || '?') }, { label: 'session', get: r => r.session }, { label: 'run', get: r => h('code', null, r.run_id) },
      { label: 'state', get: r => r.live ? pill('LIVE', 'held: ' + r.live) : chip('UNKNOWN', r.status || '—') },
      { label: 'size', num: true, get: r => bytes(r.bytes_total) }, { label: 'newest row', get: r => fmtET(r.newest_row_utc) }],
      hl.runs_without_manifest) : h('div', { class: 'dim' }, 'none'),
    h('small', null, 'capture and recovery actions stay outside this dashboard (mrofyt_recover.py on a weekend)')));
  return cards;
}
function track(r, inst) {
  const [e0, e1] = r.expected_epoch; const span = Math.max(e1 - e0, 1);
  const t = h('div', { class: 'track', title: inst + ' coverage vs expected window' });
  const d = r.instruments[inst];
  for (const [a, b] of (d.gaps_epoch || [])) t.append(h('i', { class: 'seg gap', style: `left:${100 * (a - e0) / span}%;width:${100 * (b - a) / span}%` }));
  for (const [a, b] of (d.coverage_epoch || [])) t.append(h('i', { class: 'seg cov-' + inst, style: `left:${100 * (a - e0) / span}%;width:${100 * (b - a) / span}%` }));
  for (const [a, b] of (r.shared_gaps || []).map(x => [toEpoch(x[0]), toEpoch(x[1])])) t.append(h('i', { class: 'seg shared', style: `left:${100 * (a - e0) / span}%;width:${100 * (b - a) / span}%;top:10px` }));
  return t;
}

function viewHyp(snap) {
  const hy = snap.hypotheses || {}; const fams = hy.families || [];
  const cards = [];
  if ((hy.spec_mismatch || []).length) cards.push(h('div', { class: 'banner err' }, 'registry / code mismatch: ' + hy.spec_mismatch.join(', ')));
  cards.push(h('section', { class: 'card c8' }, h('h2', null, 'Families'),
    h('small', null, 'statuses come from the exporter reading the released pilot and wave-two reports; nothing here ranks or scores'),
    table([
      { label: 'id', get: r => h('code', null, r.id) }, { label: 'wave', num: true, get: r => r.wave }, { label: 'name', get: r => r.name },
      { label: 'implementation', get: r => chip(r.implementation === 'IMPLEMENTED' ? 'READY' : r.implementation === 'CONTROL' ? 'CONTROL' : 'NOT_WIRED', r.implementation) },
      { label: 'status', get: r => chip(r.status) }, { label: 'why', get: r => (r.reasons || [])[0] || '' },
    ], fams, { onclick: r => { S.sel.hyp = r.id; render(); }, sel: r => r.id === S.sel.hyp })));
  const sel = fams.find(f => f.id === S.sel.hyp) || fams[0];
  if (sel) cards.push(h('section', { class: 'card c4' }, inspectorHyp(sel, snap)));
  const c = snap.counts || {};
  cards.push(h('section', { class: 'card c6' }, h('h2', null, 'Released counts (accrual)'),
    h('small', null, c.rule),
    c.pilot ? [h('h3', null, `wave one · ${(c.pilot.source||{}).version||''} · ${fmtET((c.pilot.source||{}).mtime_utc)}`),
      kv([['sessions inspected', (c.pilot.sessions_inspected || []).length], ['blind sessions (counted, markouts withheld)', (c.pilot.sessions_blind || []).join(', ') || 'none'],
          ['events withheld', c.pilot.events_withheld ? n0(c.pilot.events_withheld.events_withheld) : '—'], ['cooldown', c.pilot.cooldown_s + ' s']]),
      table([{ label: 'family', get: r => h('code', null, r) }, { label: 'raw firings', num: true, get: r => n0((c.pilot.raw_fires_by_family || {})[r]) },
             { label: 'distinct events', num: true, get: r => n0((c.pilot.distinct_events_by_family || {})[r]) },
             { label: 'NQ signal-source', num: true, get: r => n0((c.pilot.signal_source_events_by_family || {})[r]) }],
        ['A1', 'A2', 'A3', 'A4', 'A5', 'A6']),
      h('small', null, c.pilot.raw_fire_caveat)] : h('div', { class: 'dim' }, 'no pilot report'),
    c.wave2 ? [h('h3', null, `wave two · ${(c.wave2.source||{}).version||''} · ${fmtET((c.wave2.source||{}).mtime_utc)} · ${c.wave2.windows} windows · placebo pass ${c.wave2.placebo_pass_present ? 'present' : 'absent'}`),
      table([{ label: 'family', get: r => h('code', null, r[0]) }, { label: 'raw', num: true, get: r => n0(r[1].raw_fires) }, { label: 'events', num: true, get: r => n0(r[1].distinct_events) },
             { label: 'visible', num: true, get: r => n0(r[1].events_visible) }, { label: 'withheld', num: true, get: r => n0(r[1].events_withheld) }, { label: 'NQ source', num: true, get: r => n0(r[1].signal_source_events) }],
        Object.entries(c.wave2.families || {})),
      h('small', null, 'input unavailable (None) on: ' + JSON.stringify(c.wave2.input_unavailable || {}) + ' · arm B: ' + JSON.stringify(c.wave2.arm_b || {}))] : h('div', { class: 'dim' }, 'no wave-two report')));
  cards.push(h('section', { class: 'card c6' }, h('h2', null, 'Baselines'),
    h('p', null, h('b', null, 'z-scores: '), (hy.baselines || {}).z ? hy.baselines.z.text : ''),
    h('p', null, h('b', null, 'residual model: '), (hy.baselines || {}).resid ? hy.baselines.resid.text : ''),
    h('h2', null, 'Active levels (14)'),
    table([{ label: 'id', get: r => h('code', null, r.id) }, { label: 'family', get: r => r.family }, { label: 'definition', get: r => r.definition }, { label: 'available', get: r => r.available }], hy.levels || [])));
  cards.push(h('section', { class: 'card c6' }, h('h2', null, 'Context inventory'),
    table([{ label: 'item', get: r => r.id }, { label: 'status', get: r => chip(r.status === 'IMPLEMENTED' ? 'READY' : r.status.startsWith('NOT') || r.status.startsWith('REGISTERED') ? 'NOT_IMPLEMENTED' : 'CONDITION_FALSE', r.status) }, { label: 'where', get: r => h('code', null, r.where) }, { label: 'note', get: r => r.note }], hy.context || []),
    h('h2', { style: 'margin-top:12px' }, 'Registered, not in this version'),
    h('ul', null, ...fams.filter(f => f.implementation === 'NOT_IMPLEMENTED').map(f => h('li', null, h('b', null, f.id), ' — ', (f.reasons || [])[0])))));
  cards.push(h('section', { class: 'card' }, h('details', null, h('summary', null, 'Discrepancies found while checking earlier summaries against the frozen code (' + (hy.discrepancies || []).length + ')'),
    table([{ label: 'item', get: r => r.item }, { label: 'earlier said', get: r => r.earlier }, { label: 'verified in code', get: r => r.verified }], hy.discrepancies || []))));
  return cards;
}
function inspectorHyp(f, snap) {
  const c = snap.counts || {};
  const per = c.pilot ? (c.pilot.distinct_events_by_family_and_session || {})[f.id] : null;
  const w2 = c.wave2 ? (c.wave2.families || {})[f.id] : null;
  const bySes = per || (w2 && w2.by_session) || null;
  const br = f.breakdown || {};
  const win = f.window_et ? `${(f.window_et[0]/3600).toFixed(2)}h – ${(f.window_et[1]/3600).toFixed(2)}h ET` : 'whole session';
  return h('div', null,
    h('div', { class: 'row' }, h('h2', null, f.id + ' · ' + f.name), chip(f.status)),
    h('ul', null, ...(f.reasons || []).map(r => h('li', null, r))),
    kv([['registered in', f.registered_in], ['implemented in', h('code', null, f.implemented_in || '—')], ['implementation', f.implementation],
        ['mechanism', f.mechanism], ['direction rule', f.direction_rule], ['grid', f.grid], ['window (ET)', win],
        ['level set', Array.isArray(f.level_set) ? f.level_set.join(', ') : f.level_set], ['baseline', f.baseline ? f.baseline.text : '—'],
        ['derived from', f.derived_from || '—'], ['threshold change', f.threshold_change ? `${f.threshold_change.feature}: ${f.threshold_change.frozen} → ${f.threshold_change.variant}` : '—']]),
    (f.inputs || []).length ? [h('h3', null, 'inputs'), table([{ label: 'name', get: r => h('code', null, r.name) }, { label: 'wired', get: r => r.wired ? 'yes' : chip('NOT_WIRED', 'NO') },
      { label: 'baseline', get: r => r.baseline || '' }, { label: 'note', get: r => r.note || (r.role ? r.role : '') }], f.inputs)] : null,
    (f.conditions || []).length ? [h('h3', null, 'frozen conditions'), h('ul', { class: 'cond' }, ...f.conditions.map(cl => h('li', null, condText(cl))))] : null,
    br.first_failing_stage ? [h('h3', null, `funnel (${br.windows} windows, ${br.passed} passed, ${br.fires_recorded} fires)`),
      table([{ label: 'first failing stage', get: r => h('code', null, r[0]) }, { label: 'windows', num: true, get: r => r[1] }], Object.entries(br.first_failing_stage).sort((a, b) => b[1] - a[1])),
      (br.missing_inputs || []).length ? [h('h3', null, 'missing inputs'), table([{ label: 'input', get: r => h('code', null, r.input) }, { label: 'windows', num: true, get: r => r.windows }], br.missing_inputs)] : null] : null,
    br.checks !== undefined ? kv([['vacuum checks (2 s grid)', br.checks], ['vacuum events', br.vacuum_events], ['fires', br.fires_recorded]]) : null,
    br.windows !== undefined && br.raw_fires !== undefined ? kv([['windows', br.windows], ['input None', n0(br.input_none)], ['raw fires', br.raw_fires], ['distinct events', br.distinct_events]]) : null,
    (f.feature_availability || []).length ? [h('h3', null, 'feature availability (pilot, all sessions)'),
      table([{ label: 'feature', get: r => h('code', null, r.input) }, { label: 'available', num: true, get: r => `${r.available} / ${r.windows}` }, { label: '%', num: true, get: r => pct(r.available_frac) }], f.feature_availability)] : null,
    bySes ? [h('h3', null, 'distinct events by session (accrual only)'), table([{ label: 'session', get: r => r[0] }, { label: 'events', num: true, get: r => r[1] }], Object.entries(bySes).sort())] : null);
}
function condText(cl) {
  if (cl.op === 'any') return 'any of: ' + cl.clauses.map(c => condText(c)).join(' | ');
  return cl.feature + ' ' + (cl.op === 'is_true' ? 'is true' : cl.op + ' ' + cl.value);
}

function viewProv(snap) {
  const ses = (snap.sessions || []).slice().sort((a, b) => b.session < a.session ? -1 : 1);
  const cards = [];
  cards.push(h('section', { class: 'card c8' }, h('h2', null, 'Session timeline'),
    h('div', { class: 'legend' }, h('span', null, h('i', { style: 'background:var(--nq)' }), 'recorder run'), h('span', null, h('i', { class: 'seg recon', style: 'position:static;background:var(--nq)' }), 'reconstructed'),
      h('span', null, h('i', { class: 'seg orphan', style: 'position:static' }), 'orphan'), h('span', null, h('i', { class: 'seg open', style: 'position:static' }), 'open'), h('span', null, h('i', { class: 'seg fail', style: 'position:static;background:var(--nq)' }), 'audit failed'),
      h('span', { class: 'dim' }, 'times in America/New_York (DST-aware); UTC in the inspector')),
    ...ses.map(s => h('div', { style: 'margin:8px 0' },
      h('div', { class: 'row' }, h('a', { href: '#', onclick: (e) => { e.preventDefault(); S.sel.session = s.session; S.sel.run = null; render(); } }, h('b', null, s.session)), chip(s.session_class),
        h('small', null, `${fmtET(s.expected_utc[0])} → ${fmtET(s.expected_utc[1])}${s.expected_clipped_to_now ? ' (in progress)' : ''}`)),
      ...['NQ', 'MNQ'].map(i => h('div', { class: 'row', style: 'gap:6px' }, chip(i), runTrack(s, i)))))));
  const sel = ses.find(s => s.session === S.sel.session) || ses[0];
  if (sel) {
    const runs = ['NQ', 'MNQ'].flatMap(i => (sel.instruments[i].runs || []).map(r => Object.assign({ _inst: i }, r)));
    const r = runs.find(x => x.run_id === S.sel.run) || runs[0];
    cards.push(h('section', { class: 'card c4' }, h('h2', null, 'Session ' + sel.session), chip(sel.session_class),
      kv([['expected (ET)', `${fmtET(sel.expected_utc[0])} → ${fmtET(sel.expected_utc[1])}`], ['expected (UTC)', `${fmtUTC(sel.expected_utc[0])} → ${fmtUTC(sel.expected_utc[1])}`],
          ['NQ covered', `${ago(sel.instruments.NQ.covered_s)} of ${ago(sel.instruments.NQ.expected_s)} (${pct(sel.instruments.NQ.covered_frac)})`],
          ['MNQ covered', `${ago(sel.instruments.MNQ.covered_s)} of ${ago(sel.instruments.MNQ.expected_s)} (${pct(sel.instruments.MNQ.covered_frac)})`],
          ['gaps NQ / MNQ', `${sel.instruments.NQ.gaps.length} / ${sel.instruments.MNQ.gaps.length}`], ['shared gaps', sel.shared_gaps.length ? sel.shared_gaps.map(g => `${fmtETt(g[0])}–${fmtETt(g[1])}`).join(', ') : 'none'],
          ['pair overlap', sel.pair_overlap_frac === null ? '—' : sel.pair_overlap_frac.toFixed(3)]]),
      h('small', null, sel.pair_note),
      h('h3', null, 'runs'),
      table([{ label: 'inst', get: x => chip(x._inst) }, { label: 'run', get: x => h('code', null, x.run_id) }, { label: 'source', get: x => x.source },
             { label: 'audit', get: x => x.audit && x.audit.ok === true ? 'ok' : x.audit && x.audit.ok === false ? chip('INVALID_OR_MISSING_DATA', 'FAIL') : '—' }], runs,
        { onclick: x => { S.sel.run = x.run_id; render(); }, sel: x => r && x.run_id === r.run_id }),
      r ? inspectorRun(r, snap) : null));
  }
  return cards;
}
function runTrack(s, inst) {
  const [e0, e1] = s.expected_epoch; const span = Math.max(e1 - e0, 1);
  const t = h('div', { class: 'track', style: 'flex:1' });
  for (const r of (s.instruments[inst].runs || [])) {
    if (!r.first_recv_epoch) continue;
    const a = r.first_recv_epoch, b = r.last_recv_epoch || a;
    const cls = ['seg', 'cov-' + inst, r.source === 'reconstructed' ? 'recon' : '', r.source === 'open' ? 'open' : '', r.source === 'orphan' ? 'orphan' : '', r.audit && r.audit.ok === false ? 'fail' : ''].join(' ');
    const seg = h('i', { class: cls, style: `left:${100 * (a - e0) / span}%;width:${Math.max(100 * (b - a) / span, 0.3)}%`, title: `${r.run_id} ${fmtETt(a)}–${fmtETt(b)}` });
    seg.addEventListener('click', () => { S.sel.session = s.session; S.sel.run = r.run_id; render(); });
    t.append(seg);
  }
  for (const [a, b] of (s.shared_gaps || []).map(x => [toEpoch(x[0]), toEpoch(x[1])])) t.append(h('i', { class: 'seg shared', style: `left:${100 * (a - e0) / span}%;width:${100 * (b - a) / span}%;top:10px` }));
  return t;
}
function inspectorRun(r, snap) {
  const a = r.audit || {}; const ing = r.ingest || {}; const rc = r.recorder_counters || {};
  const src = (snap.reports || {});
  return h('div', null, h('h3', null, 'run ' + r.run_id),
    kv([['source', r.source + (r.reconstructed_by ? ' by ' + r.reconstructed_by : '')], ['manifest', r.manifest ? h('code', null, r.manifest) : '— (none)'],
        ['capture instance', r.capture_instance], ['contract', r.contract], ['build', r.build], ['close reason', r.close_reason],
        ['first row', fmtET(r.first_recv_utc)], ['last row', fmtET(r.last_recv_utc)], ['UTC', `${fmtUTC(r.first_recv_utc)} → ${fmtUTC(r.last_recv_utc)}`],
        ['streams', r.streams ? Object.entries(r.streams).map(([k, v]) => `${k} ${bytes(v.bytes)} / ${n0(v.rows)} rows`).join(' · ') : '—'],
        ['recorder counters', Object.keys(rc).length ? Object.entries(rc).map(([k, v]) => `${k}=${v}`).join(' ') : (r.source === 'reconstructed' ? 'ABSENT by design (reconstructed)' : '—')],
        ['audit', a.ok === true ? 'ok' : a.ok === false ? 'FAILED: ' + (a.failure_codes || []).join(', ') : (a.note || '—')],
        ['rows (audit)', n0(a.rows)], ['event seq', a.seq_first !== undefined ? `${a.seq_first} → ${a.seq_last}` : '—'],
        ['feed disconnects', n0(a.disconnects)], ['book ready / resyncs', a.book_ready !== undefined ? `${a.book_ready} / ${a.book_resync_starts} (spurious ${a.spurious_book_ready})` : '—'],
        ['depth rows', a.depth_rows !== undefined ? `${a.depth_rows} · sides ${(a.depth_sides || []).join('/')} · actions ${(a.depth_actions || []).join('/')}` : '—'],
        ['latency p50/p95', a.latency_ms ? `${a.latency_ms.p50} / ${a.latency_ms.p95} ms` : '—'], ['rows in disconnect gaps', n0(a.suppressed_rows)],
        ['ingest', ing.skipped ? `SKIPPED ${ing.skipped}${ing.reason ? ': ' + (Array.isArray(ing.reason) ? ing.reason.join('; ') : ing.reason) : ''}` : ing.skipped === false || ing.rows_ingested !== undefined ? `${n0(ing.rows_ingested)} rows` : (ing.note || '—')],
        ['recovery', r.recovery_status || '—'], ['newest row (open/orphan)', r.newest_row_utc ? fmtET(r.newest_row_utc) : '—']]),
    h('h3', null, 'provenance of these facts'),
    kv([['audit report', src.audit ? `${src.audit.path || src.audit.error} · ${src.audit.version || ''} · ${fmtET(src.audit.mtime_utc)}` : '—'],
        ['ledger', src.ledger ? `${src.ledger.path || src.ledger.error} · ${src.ledger.version || ''} · ${fmtET(src.ledger.mtime_utc)}` : '—'],
        ['recovery report', src.recovery ? `${src.recovery.path || src.recovery.error} · ${src.recovery.version || ''} · ${fmtET(src.recovery.mtime_utc)}` : '—'],
        ['snapshot', snap.generated_utc]]),
    h('small', null, 'Original finalized capture, recovered copies and orphans are distinguished by "source". No historical price data supplements any run here; missing order-flow data is shown as a gap, never filled.'));
}

// ---------------------------------------------------------------- replay
function viewReplay(snap) {
  const rp = S.rp; const ex = (snap.exposed || {}).sessions || {};
  const allSes = (snap.sessions || []).map(s => s.session);
  const cards = [];
  if (!S.data.replay_available) cards.push(h('div', { class: 'banner unav' }, 'Replay unavailable on this computer: no capture folder and/or no readable exposure ledger configured. Health, readiness and provenance still work from the exported snapshot.'));
  const left = h('div', { class: 'card' }, h('h2', null, 'Select'),
    h('div', { class: 'row' }, h('label', null, 'session ', h('select', { onchange: (e) => { rp.session = e.target.value || null; rp.windows = null; rp.approach = null; rp.window = null; rp.bundle = null; loadWindows(); } },
      h('option', { value: '' }, '—'), ...allSes.map(s => { const cls = (snap.sessions.find(x => x.session === s) || {}).session_class; const ok = !!ex[s] && cls === 'EXPOSED';
        return h('option', { value: s, disabled: ok ? null : 'disabled', selected: rp.session === s ? 'selected' : null }, s + (ok ? '' : '  (' + cls + ' — not inspectable)')); }))),
      h('label', null, 'instrument ', h('select', { onchange: (e) => { rp.instrument = e.target.value; rp.approach = null; rp.window = null; rp.bundle = null; loadWindows(); } },
        ...['NQ', 'MNQ'].map(i => h('option', { value: i, selected: rp.instrument === i ? 'selected' : null }, i))))),
    h('small', null, 'only sessions the exposure ledger labels EXPOSED can be opened; the server refuses every other request'),
    rp.winErr ? h('div', { class: 'banner err' }, rp.winErr) : null);
  if (rp.session && ex[rp.session]) {
    const aps = (ex[rp.session].approaches || {})[rp.instrument] || [];
    left.append(h('h3', null, `approaches (${aps.length})`),
      h('div', { class: 'list' }, ...aps.map(a => h('div', { class: 'item' + (rp.approach && rp.approach.approach_id === a.approach_id ? ' sel' : ''), onclick: () => { rp.approach = a; rp.window = null; rp.bundle = null; render(); } },
        h('div', null, h('code', null, a.level_id), ' ', h('small', null, fpx(a.level_px)), ' ', chip(a.ad > 0 ? 'NQ' : 'MNQ', a.ad > 0 ? 'from below ↑' : 'from above ↓')),
        h('small', null, `${fmtETt(a.t0)} · ${a.n_windows} windows · run ${a.run}`)))));
    if (rp.approach) {
      const ws = (rp.windows || []).filter(w => String(w.approach_id) === String(rp.approach.approach_id));
      left.append(h('h3', null, '10-second decision windows'),
        rp.windows ? h('div', { class: 'list' }, ...ws.map(w => h('div', { class: 'item' + (rp.window && rp.window.t_end === w.t_end ? ' sel' : ''), onclick: () => selectWindow({ i: w.window_index, t_start: w.t_start, t_end: w.t_end, wall_state: w.wall_state }) },
          `#${w.window_index}  ${fmtETt(w.t_start)} → ${fmtETt(w.t_end)}  `, h('small', null, w.wall_state))))
                   : h('div', { class: 'dim' }, rp.winErr || 'loading windows from the server…'));
    }
  }
  const mid = h('div', { class: 'card' });
  const right = h('div', { class: 'card' });
  if (rp.window) {
    const b = rp.bundle;
    mid.append(h('div', { class: 'row' }, h('h2', null, `${rp.session} · ${rp.instrument} · ${rp.approach.level_id} @ ${fpx(rp.approach.level_px)} · window #${rp.window.i}`)));
    if (rp.bErr) mid.append(h('div', { class: 'banner err' }, rp.bErr));
    if (!b && !rp.bErr) mid.append(h('div', { class: 'notice' }, 'loading bounded window…'));
    if (b) {
      const cv = h('canvas', { width: 900, height: 320 }); mid.append(cv);
      const dcv = h('canvas', { width: 900, height: 120 }); mid.append(dcv);
      const ctl = h('div', { class: 'controls' },
        h('button', { onclick: () => { rp.playing = !rp.playing; tick(); } }, rp.playing ? '⏸ pause' : '▶ play'),
        h('button', { onclick: () => step(-1) }, '◀ 250 ms'), h('button', { onclick: () => step(1) }, '250 ms ▶'),
        h('input', { type: 'range', min: 0, max: Math.max(b.depth_snapshots.length - 1, 0), value: rp.cursor, oninput: (e) => { rp.cursor = +e.target.value; drawAll(); } }),
        h('span', { class: 'mono', id: 'cursor-t' }, ''));
      mid.append(ctl);
      mid.append(h('small', null, `${b.depth_note}. Read ${bytes(b.bytes_read)} in bounded seeks${b.truncated ? ' — TRUNCATED by the row cap' : ''}; gaps ${b.gaps.length}; book events ${b.book_invalid.length}.`));
      const ladder = h('div', { class: 'ladder', id: 'ladder' });
      const tape = h('div', { class: 'tape', id: 'tape' });
      right.append(h('h3', null, 'depth (top 10, frozen KLevelBook)'), ladder, h('h3', null, 'time & sales'), tape);
      rp._cv = cv; rp._dcv = dcv;
      setTimeout(drawAll, 0);
    }
    right.append(h('h3', null, 'detector evidence at this window'), evidence());
  } else {
    mid.append(h('div', { class: 'notice' }, 'Pick an exposed session, an instrument, a level approach and a decision window. Candles, key levels, tape, quotes and depth are read from the raw capture for that window only.'));
  }
  cards.push(h('div', { class: 'card', style: 'padding:0;border:none;background:none' }, h('div', { class: 'replay-grid' }, left, mid, right)));
  return cards;
}
async function loadWindows() {
  const rp = S.rp; rp.winErr = null; rp.windows = null;
  if (!rp.session) { render(); return; }
  try {
    const r = await fetch(`/api/replay/windows?session=${encodeURIComponent(rp.session)}&instrument=${rp.instrument}`);
    const d = await r.json();
    if (!r.ok) rp.winErr = (d.refused ? 'REFUSED by policy: ' : 'error: ') + d.error;
    else rp.windows = d.windows;
  } catch (e) { rp.winErr = String(e); }
  render();
}
async function selectWindow(w) {
  const rp = S.rp; rp.window = w; rp.bundle = null; rp.bErr = null; rp.cursor = 0; rp.playing = false; rp.explain = null;
  render();
  try {
    const q = `session=${encodeURIComponent(rp.session)}&instrument=${rp.instrument}&run=${encodeURIComponent(rp.approach.run)}&t_start=${w.t_start}&t_end=${w.t_end}`;
    const [rb, re] = await Promise.all([fetch('/api/replay/bundle?' + q), fetch(`/api/replay/explain?session=${encodeURIComponent(rp.session)}&instrument=${rp.instrument}&t_end=${w.t_end}`)]);
    const b = await rb.json(); const e = await re.json();
    if (!rb.ok) rp.bErr = (b.refused ? 'REFUSED by policy: ' : 'error: ') + b.error; else rp.bundle = b;
    if (re.ok) rp.explain = e;
  } catch (err) { rp.bErr = String(err); }
  render();
}
function step(d) { const rp = S.rp; if (!rp.bundle) return; rp.cursor = Math.max(0, Math.min(rp.bundle.depth_snapshots.length - 1, rp.cursor + d)); drawAll(); }
function tick() {
  const rp = S.rp; if (rp.timer) { clearTimeout(rp.timer); rp.timer = null; }
  if (!rp.playing || !rp.bundle) { render(); return; }
  if (rp.cursor >= rp.bundle.depth_snapshots.length - 1) { rp.playing = false; render(); return; }
  rp.cursor++; drawAll(); rp.timer = setTimeout(tick, 250);
}
function drawAll() {
  const rp = S.rp; const b = rp.bundle; if (!b || !rp._cv) return;
  const snap = b.depth_snapshots[rp.cursor]; const tc = snap ? snap[0] : b.window.display_from;
  const lab = document.getElementById('cursor-t'); if (lab) lab.textContent = `${fmtETt(tc)} ET · ${fmtUTC(tc)} · ${(tc - b.window.t_start).toFixed(2)} s from window start`;
  drawCandles(rp._cv, b, tc); drawFlow(rp._dcv, b, tc); drawLadder(snap); drawTape(b, tc);
}
function drawCandles(cv, b, tc) {
  const ctx = cv.getContext('2d'); const W = cv.width, H = cv.height; ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0f1216'; ctx.fillRect(0, 0, W, H);
  const cs = b.candles; if (!cs.length) { ctx.fillStyle = '#98a3ae'; ctx.fillText('no trades in the read window', 10, 20); return; }
  const lv = Object.entries((S.rp.window && (S.rp.explain && S.rp.explain.window.levels)) || {}).filter(([, v]) => v !== null);
  let lo = Math.min(...cs.map(c => c.l)), hi = Math.max(...cs.map(c => c.h));
  for (const [, v] of lv) { if (v > lo && v < hi) continue; if (Math.abs(v - (lo + hi) / 2) < (hi - lo) * 3) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const t0 = cs[0].t_open, t1 = cs[cs.length - 1].t_open + 60;
  const X = (t) => 40 + (W - 50) * (t - t0) / (t1 - t0), Y = (p) => 10 + (H - 30) * (1 - (p - lo) / (hi - lo));
  ctx.font = '11px monospace';
  // decision window and display window
  ctx.fillStyle = 'rgba(111,177,255,0.10)'; ctx.fillRect(X(b.window.display_from), 0, X(b.window.display_to) - X(b.window.display_from), H);
  ctx.fillStyle = 'rgba(111,177,255,0.25)'; ctx.fillRect(X(b.window.t_start), 0, X(b.window.t_end) - X(b.window.t_start), H);
  // levels
  // labels are pushed apart when two levels sit within a text height of each other; the lines stay exactly at the level
  let lastLabelY = -100;
  for (const [id, v] of lv.slice().sort((a, b) => Y(a[1]) - Y(b[1]))) {
    ctx.strokeStyle = '#e0b341'; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(40, Y(v)); ctx.lineTo(W - 10, Y(v)); ctx.stroke(); ctx.setLineDash([]);
    const ly = Math.max(Y(v) - 2, lastLabelY + 12); lastLabelY = ly;
    ctx.fillStyle = '#e0b341'; ctx.fillText(id + ' ' + fpx(v), 44, ly);
  }
  // candles
  const cw = Math.max(2, (W - 50) / cs.length * 0.7);
  for (const c of cs) { const x = X(c.t_open + 30); const up = c.c >= c.o; ctx.strokeStyle = ctx.fillStyle = up ? '#3fbf7f' : '#e06c5d';
    ctx.beginPath(); ctx.moveTo(x, Y(c.h)); ctx.lineTo(x, Y(c.l)); ctx.stroke(); ctx.fillRect(x - cw / 2, Y(Math.max(c.o, c.c)), cw, Math.max(1, Math.abs(Y(c.o) - Y(c.c)))); }
  // gaps
  ctx.fillStyle = 'rgba(224,108,93,0.25)'; for (const [a, z] of b.gaps) ctx.fillRect(X(a), 0, Math.max(X(z) - X(a), 2), H);
  // fires on this session near the window
  const fires = ((S.data.snapshot.exposed.sessions[S.rp.session] || {}).fires || []).filter(f => f.instrument === S.rp.instrument && f.t >= t0 && f.t <= t1);
  for (const f of fires) { ctx.fillStyle = f.wave === 1 ? '#6fb1ff' : '#b565d9'; ctx.beginPath(); ctx.moveTo(X(f.t), H - 20); ctx.lineTo(X(f.t) - 5, H - 10); ctx.lineTo(X(f.t) + 5, H - 10); ctx.fill(); ctx.fillText(f.family + (f.direction > 0 ? '↑' : '↓'), X(f.t) + 6, H - 12); }
  // cursor + axes
  ctx.strokeStyle = '#6fb1ff'; ctx.beginPath(); ctx.moveTo(X(tc), 0); ctx.lineTo(X(tc), H); ctx.stroke();
  ctx.fillStyle = '#98a3ae'; ctx.fillText(hi.toFixed(2), 2, 14); ctx.fillText(lo.toFixed(2), 2, H - 22);
  ctx.fillText(fmtETt(t0), 40, H - 4); ctx.fillText(fmtETt(t1), W - 90, H - 4);
  ctx.fillText('1-min candles (display only) · window shaded · levels as the runner held them · ▲ fires', 120, H - 4);
}
function drawFlow(cv, b, tc) {
  const ctx = cv.getContext('2d'); const W = cv.width, H = cv.height; ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#0f1216'; ctx.fillRect(0, 0, W, H);
  const t0 = b.window.display_from, t1 = b.window.display_to; const X = (t) => 40 + (W - 50) * (t - t0) / (t1 - t0);
  const bb = b.bbo; if (!bb.length) return;
  const lo = Math.min(...bb.map(q => q[1])), hi = Math.max(...bb.map(q => q[3])); const pad = (hi - lo) * 0.1 || 0.25;
  const Y = (p) => 8 + (H - 26) * (1 - (p - (lo - pad)) / ((hi + pad) - (lo - pad)));
  ctx.font = '11px monospace';
  ctx.fillStyle = 'rgba(111,177,255,0.25)'; ctx.fillRect(X(b.window.t_start), 0, X(b.window.t_end) - X(b.window.t_start), H);
  for (let k = 0; k < 4; k++) { const x = X(b.window.t_start + 2.5 * k); ctx.strokeStyle = '#2a323b'; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  ctx.strokeStyle = '#9fe0bd'; ctx.beginPath(); bb.forEach((q, i) => { const x = X(q[0]), y = Y(q[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke();
  ctx.strokeStyle = '#f0b4ab'; ctx.beginPath(); bb.forEach((q, i) => { const x = X(q[0]), y = Y(q[3]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke();
  for (const tr of b.tape) { ctx.fillStyle = tr[3] === 'BUY' ? '#3fbf7f' : tr[3] === 'SELL' ? '#e06c5d' : '#8b96a1'; const r = Math.min(6, 1.5 + Math.sqrt(tr[2] || 1)); ctx.beginPath(); ctx.arc(X(tr[0]), Y(tr[1]), r, 0, 6.28); ctx.fill(); }
  ctx.fillStyle = 'rgba(224,108,93,0.3)'; for (const [a, z] of b.gaps) ctx.fillRect(X(a), 0, Math.max(X(z) - X(a), 2), H);
  ctx.strokeStyle = '#6fb1ff'; ctx.beginPath(); ctx.moveTo(X(tc), 0); ctx.lineTo(X(tc), H); ctx.stroke();
  ctx.fillStyle = '#98a3ae'; ctx.fillText('BBO (bid green / ask red) and prints; 2.5 s persistence grid inside the 10 s window; red = gap or invalid book', 44, H - 4);
}
function drawLadder(snap) {
  const el = document.getElementById('ladder'); if (!el) return; el.innerHTML = '';
  if (!snap) { el.append(h('div', { class: 'unknown' }, 'no depth snapshot at cursor')); return; }
  const [, bids, asks] = snap;
  if (!bids.length && !asks.length) { el.append(h('div', { class: 'unknown' }, 'book empty at this instant: no depth update has been replayed yet (the rebuild starts 60 s before the window; nothing is invented)')); return; }
  for (let i = 9; i >= 0; i--) { const a = asks[i]; el.append(h('div', { class: 'lv' }, h('span', null, ''), h('span', { class: 'px ' + (a ? '' : 'unknown') }, a ? fpx(a[0]) : 'unknown'), h('span', { class: 'ask' }, a ? a[1] : ''))); }
  el.append(h('div', { class: 'lv', style: 'border-top:1px solid var(--line)' }));
  for (let i = 0; i < 10; i++) { const bd = bids[i]; el.append(h('div', { class: 'lv' }, h('span', { class: 'bid' }, bd ? bd[1] : ''), h('span', { class: 'px ' + (bd ? '' : 'unknown') }, bd ? fpx(bd[0]) : 'unknown'), h('span', null, ''))); }
  el.append(h('small', null, 'displayed size only; executed volume is on the tape; withdrawal is inferred, never shown as executed'));
}
function drawTape(b, tc) {
  const el = document.getElementById('tape'); if (!el) return; el.innerHTML = '';
  const rows = b.tape.filter(t => t[0] <= tc).slice(-40).reverse();
  el.append(h('div', { class: 'dim' }, ...['time', 'px', 'sz', 'side*', 'conf'].map(x => h('span', null, x))));
  for (const t of rows) el.append(h('div', { class: t[3] === 'BUY' ? 'buy' : t[3] === 'SELL' ? 'sell' : '' }, ...[fmtETt(t[0]), fpx(t[1]), t[2], t[3] || '?', t[4] || '?'].map(x => h('span', null, x))));
  if (!rows.length) el.append(h('div', { class: 'unknown' }, h('span', { style: 'grid-column: 1 / -1' }, 'no prints at or before the cursor in this bounded read')));
  el.append(h('small', null, '*aggressor side is INFERRED (QUOTE_TEST_v1); conf HIGH/LOW; no individual participant is identified'));
}
function evidence() {
  const rp = S.rp; const e = rp.explain; if (!e) return h('div', { class: 'dim' }, 'loading…');
  const w = e.window; const out = h('div', null);
  const fires = ((S.data.snapshot.exposed.sessions[rp.session] || {}).fires || []).filter(f => f.instrument === rp.instrument && Math.abs(f.t - w.t_end) < 0.01);
  out.append(kv([['approached', `${w.level_id} @ ${fpx(w.level_px)} (${w.family})`], ['direction of approach', w.ad > 0 ? 'from below (ad=+1)' : 'from above (ad=−1)'],
    ['window', `#${w.window_index} ${fmtETt(w.t_start)} → ${fmtETt(w.t_end)} ET`], ['wall state', w.wall_state], ['signal source instrument', rp.instrument === 'NQ' ? 'yes (NQ)' : 'no (MNQ is not the signal source)'],
    ['fires at this window', fires.length ? fires.map(f => `${f.family} ${f.direction > 0 ? 'long' : 'short'} (wave ${f.wave})`).join(', ') : 'none'],
    ['raw firing vs event', fires.length ? dedupNote(fires[0]) : '—']]));
  for (const [hid, ex] of Object.entries(e.explain)) {
    const det = h('details', ex.all_passed ? { open: 'open' } : null, h('summary', null, h('code', null, hid), ' ', ex.all_passed ? chip('READY', 'all conditions held') : ex.inputs_missing.length ? chip('NO_QUALIFYING_OBSERVATIONS', 'inputs missing: ' + ex.inputs_missing.join(', ')) : chip('CONDITION_FALSE', 'a condition failed')),
      h('ul', { class: 'cond' }, ...ex.gate.map(c => condLine(c, 'gate')), ...ex.conditions.map(c => condLine(c))));
    out.append(det);
  }
  out.append(h('small', null, 'research events, not trades: nothing here is a fill, a stop or an outcome'));
  return out;
}
function condLine(c, tag) {
  if (c.op === 'any') return h('li', null, 'any of: ', ...c.clauses.map(s => condLine(s)), h('span', { class: c.passed ? 'ok' : 'no' }, c.passed ? ' ✓' : ' ✗'));
  const cls = c.passed === true ? 'ok' : c.passed === false ? 'no' : 'na';
  return h('li', null, (tag ? tag + ': ' : ''), `${c.feature} ${c.op === 'is_true' ? 'is true' : c.op + ' ' + c.value}  `, h('span', { class: cls }, c.passed === null ? '— (None)' : c.passed ? '✓' : '✗'), h('span', { class: 'dimmer' }, `  observed ${c.observed === null || c.observed === undefined ? 'None' : c.observed}`));
}
function dedupNote(f) {
  // the pilot's own rule (mrofyt_pilot.dedup_fires): same instrument, session, family, direction, within 60 s of the event's FIRST firing
  const all = ((S.data.snapshot.exposed.sessions[S.rp.session] || {}).fires || []).filter(x => x.instrument === f.instrument && x.family === f.family && x.direction === f.direction && x.wave === f.wave).sort((a, b) => a.t - b.t);
  let first = null; let isFirst = false;
  for (const x of all) { if (first === null || x.t - first > 60) { first = x.t; if (Math.abs(x.t - f.t) < 1e-6) isFirst = true; } else if (Math.abs(x.t - f.t) < 1e-6) isFirst = false; }
  return isFirst ? 'FIRST firing of a distinct event (60 s cooldown, per mrofyt_pilot.dedup_fires)' : 'a repeat firing inside an event already counted';
}

// ---------------------------------------------------------------- render
function setView(v) { S.view = v; for (const b of document.querySelectorAll('#nav button')) b.classList.toggle('on', b.dataset.view === v); render(); }
function render() {
  renderStrip(); renderBanners(); renderFooter();
  const m = document.getElementById('main'); m.innerHTML = '';
  const d = S.data; const snap = d && d.snapshot;
  if (!snap) { m.append(h('section', { class: 'card' }, h('h2', null, 'UNAVAILABLE'), h('p', null, (d && d.snapshot_error) || S.err || 'no data'), h('p', { class: 'dim' }, 'Run the exporter (godseye_export.py) and refresh. A missing snapshot is never shown as zero of anything.'))); return; }
  const cards = S.view === 'health' ? viewHealth(snap) : S.view === 'hyp' ? viewHyp(snap) : S.view === 'prov' ? viewProv(snap) : viewReplay(snap);
  for (const c of cards) m.append(c);
}
document.querySelectorAll('#nav button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
load(); setInterval(load, 60000);
