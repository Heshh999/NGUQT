#!/usr/bin/env python3
"""mrofyt_levelbreak.py - MROF-YT-W6-LEVELBREAK-1.0

MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md, part A, turned into running
code: the one idea family with support -- a big level breaks; fade it
when the break fails (L2, break and reclaim), follow it when it holds
(L4, break and retest) -- with the stop questions the operator asked.

    T1  L2, fixed stop 60 ticks (15 points)
    T2  L2, STRUCTURAL stop: 2 ticks beyond the sweep's extreme, at
        least 12 and at most 60 ticks from entry
    T3  L2, FLOW-INVALIDATION exit: out when the push resumes (10 s
        aggressor delta back in the break direction, z >= 1.5) with
        price back through the level; 80-tick emergency stop
    T4  L4, fixed stop 60 ticks
    T5  L2, fixed stop 60 ticks, only when the TRAPPED volume (aggressive
        contracts traded beyond the level in the break direction during
        the approach) is at least the DEV median

Every test: target 100 ticks, 1800 s, mid-to-mid path, then charged
mrofyt_costs's round trip (commission, a tick of spread, a tick of slip
on stops). The test is the mean NET result per trade above zero,
session-clustered, Holm over the five on NQ.

    python3 mrofyt_levelbreak.py "<capture>" --out w6.json \\
            --frozen-out w6_frozen.json           # DEV: seen days, not a test
    python3 mrofyt_levelbreak.py "<replay folder>" --evaluate w6_frozen.json \\
            --holdout --out w6_replay.json        # untouched replay days, once
    python3 mrofyt_levelbreak.py "<capture>" --evaluate w6_frozen.json \\
            --unblind --out w6_eval.json          # CHECKPOINT ONLY

The runner subclasses wave three's; hooks only. A --holdout folder may
hold only sessions before 2026-09-01 (Market Replay recordings) and is
refused otherwise.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import copy
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W6_VERSION = 'MROF-YT-W6-LEVELBREAK-1.0'
REGISTRATION = 'MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = '20260901'
HOLDOUT_LEDGER = 'MROF_REPLAY_HOLDOUT_EXPOSURE.json'
TICK = SIG.TICK

# registration A2: the exits
TARGET = 100.0
FIXED_STOP = 60.0
STRUCT_BUFFER = 2.0
STRUCT_MIN, STRUCT_MAX = 12.0, 60.0
DISASTER = 80.0
FLOW_Z = 1.5
LIMIT_S = 1800.0

TESTS = (('T1', 'L2', 'fixed'), ('T2', 'L2', 'structural'),
         ('T3', 'L2', 'flow'), ('T4', 'L4', 'fixed'),
         ('T5', 'L2', 'trapped'))
FAMILIES = ('L2', 'L4')
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# pure pieces
# ---------------------------------------------------------------------
def path_exit(ts, ps, i, d, target, stop, limit_s=LIMIT_S, exit_t=None,
              exit_px=None):
    """One trade from compressed index i, direction d, on the run's mid
    path: TARGET (+target), STOP (-stop), INVALIDATED (an outside exit at
    exit_t, at exit_px, whenever it comes before either), TIMEOUT (the
    last mid at or before the limit) or UNRESOLVED (the run ends first).
    Returns (outcome, value_ticks, seconds)."""
    t0, p0 = ts[i], ps[i]
    t_end = t0 + limit_s
    n = len(ps)
    j = i + 1
    while j < n and ts[j] <= t_end:
        if exit_t is not None and ts[j] > exit_t:
            return 'INVALIDATED', d * (exit_px - p0) / TICK, exit_t - t0
        x = d * (ps[j] - p0) / TICK
        if x <= -stop:
            return 'STOP', -stop, ts[j] - t0
        if x >= target:
            return 'TARGET', target, ts[j] - t0
        j += 1
    if exit_t is not None and exit_t <= t_end and exit_t <= ts[-1]:
        return 'INVALIDATED', d * (exit_px - p0) / TICK, exit_t - t0
    if ts[-1] < t_end:
        return 'UNRESOLVED', None, None
    k = bisect.bisect_right(ts, t_end) - 1
    return 'TIMEOUT', d * (ps[k] - p0) / TICK, ts[k] - t0


def structural_stop(ad, touch, p0):
    """Ticks from entry to 2 ticks beyond the sweep's extreme (the
    approach's touch, on the break side), clamped to [12, 60]."""
    if touch is None or p0 is None:
        return None
    dist = ad * (touch - p0) / TICK + STRUCT_BUFFER
    return min(STRUCT_MAX, max(STRUCT_MIN, dist))


def flow_invalidation(grid, t0, ad, level_px, limit_s=LIMIT_S):
    """grid: [(t, record)] of the trade's own run, time-ordered. The
    first grid tick strictly after t0 at which the 10 s aggressor delta
    is back in the break direction with z >= 1.5 AND the mid is back
    through the level by a tick; (t, mid) or None."""
    k = bisect.bisect_right([x[0] for x in grid], t0)
    for t, g in grid[k:]:
        if t > t0 + limit_s:
            break
        D, z, mid = g.get('D'), g.get('z_delta_s'), g.get('mid')
        if not D or z is None or mid is None:
            continue
        if (1 if D > 0 else -1) == ad and z >= FLOW_Z and \
                ad * (mid - level_px) >= TICK - 1e-9:
            return t, mid
    return None


# ---------------------------------------------------------------------
# the runner: wave three's plus what the stops and filters need
# ---------------------------------------------------------------------
class LevelBreakRunner(BM.BigMoveRunner):
    """Wave three's runner; every L2/L4 fire also carries its level
    price, the approach's direction and sweep extreme, and the trapped
    volume of its approach. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        BM.BigMoveRunner.__init__(self, capture_dir, mode='real',
                                  unblind=unblind, **kw)
        self.holdout = holdout
        self.trapped = {}                 # (instrument, approach id) -> qty
        self.ledger['wave6'] = dict(version=W6_VERSION)

    def plan(self):
        if not self.holdout:
            return BM.BigMoveRunner.plan(self)
        plan = PI.PilotRunner.plan(self)
        late = sorted({ses for _i, ses, _r in plan if ses >= HOLDOUT_BEFORE})
        if late:
            raise RUN.NoCaptureData(
                'a replay holdout folder may hold only sessions before %s; '
                '%s holds %s. Nothing was read.' % (
                    HOLDOUT_BEFORE, self.dir, ', '.join(late)))
        return plan

    def _close_session(self, st):
        BM.BigMoveRunner._close_session(self, st)
        for k in [k for k in self.trapped if k[0] == st.instrument]:
            del self.trapped[k]

    def _mark_run(self, st):
        mark = BM.BigMoveRunner._mark_run(self, st)
        mark['w6'] = copy.deepcopy(self.trapped)
        return mark

    def _unwind_run(self, st, mark):
        BM.BigMoveRunner._unwind_run(self, st, mark)
        self.trapped = mark['w6']

    def _on_trade_event(self, st, t, e):
        BM.BigMoveRunner._on_trade_event(self, st, t, e)
        if not st.trades or not st.approaches:
            return
        _t, px, sz, sign = st.trades[-1]
        if not sign:
            return
        for ap in st.approaches.values():
            if ap.active and sign == ap.ad and \
                    ap.ad * (px - ap.level_px) >= TICK - 1e-9:
                key = (st.instrument, ap.id)
                self.trapped[key] = self.trapped.get(key, 0.0) + sz

    def _w3_fire(self, st, pat, direction, t, ap, g):
        BM.BigMoveRunner._w3_fire(self, st, pat, direction, t, ap, g)
        if ap is not None and pat in FAMILIES:
            self.w3_fires[-1].update(
                level_px=ap.level_px, ad=ap.ad, touch=ap.touch,
                trapped=self.trapped.get((st.instrument, ap.id), 0.0))


# ---------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------
def level_events(r):
    """De-duplicated L2/L4 events (the pilot's 60 s rule), each carrying
    its first fire's level price, direction, sweep extreme and trapped
    volume."""
    fires = [f for f in r.w3_fires if f['family'] in FAMILIES]
    first = {}
    for f in fires:
        first.setdefault((f['instrument'], f['session'], f['family'],
                          f['direction'], f['t']), f)
    out = []
    for e in PI.dedup_fires(fires, PI.EVENT_COOLDOWN_S):
        f = first[(e['instrument'], e['session'], e['family'],
                   e['direction'], e['t'])]
        e = dict(e)
        for k in ('level_px', 'ad', 'touch', 'trapped'):
            e[k] = f.get(k)
        out.append(e)
    return out


def score_events(r, events):
    """{test id: [(event, outcome, gross ticks, risk ticks)]} for every
    event the test takes (trapped cut applied later)."""
    paths = {k: BM.compress(ts, ps) for k, (ts, ps) in r.series.items()
             if len(ts)}
    grid = collections.defaultdict(list)
    for g in r.grid:
        grid[(g['instrument'], g['run'])].append((g['t'], g))
    out = collections.defaultdict(list)
    for e in events:
        key = (e['instrument'], e.get('run'))
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        d = e['direction']
        for tid, fam, kind in TESTS:
            if e['family'] != fam:
                continue
            if kind in ('fixed', 'trapped'):
                risk = FIXED_STOP
                res = path_exit(ts, ps, i, d, TARGET, risk)
            elif kind == 'structural':
                risk = structural_stop(e['ad'], e['touch'], ps[i])
                if risk is None:
                    continue
                res = path_exit(ts, ps, i, d, TARGET, risk)
            else:
                risk = DISASTER
                inv = flow_invalidation(grid[key], e['t'], e['ad'],
                                        e['level_px'])
                res = path_exit(ts, ps, i, d, TARGET, risk,
                                exit_t=inv[0] if inv else None,
                                exit_px=inv[1] if inv else None)
            if res[0] == 'UNRESOLVED':
                continue
            out[tid].append((e, res[0], res[1], risk, res[2]))
    return out


def trapped_cut(events, inst):
    """Registration A4: the median trapped volume of the L2 events of
    one instrument (every event, resolved or not)."""
    vals = sorted(e['trapped'] for e in events
                  if e['family'] == 'L2' and e['instrument'] == inst and
                  e.get('trapped') is not None)
    return vals[len(vals) // 2] if vals else None


def test_stats(rows, inst):
    """rows: [(event, outcome, gross ticks, risk ticks, seconds)] of one
    instrument. Net = gross - mrofyt_costs round trip; the test is the
    session-clustered mean net above zero."""
    if not rows:
        return dict(n=0, sessions=0)
    net = []
    cl = []
    for e, oc, g, risk, _s in rows:
        c = CO.cost_ticks(inst, 'STOP' if oc == 'STOP' else 'TARGET')
        x = g - c
        net.append((x, risk, oc, g))
        cl.append((e['session'], x, 0.0, x))
    st = DI.cluster_stats(cl)
    n = len(net)
    return dict(
        n=n, sessions=st.get('sessions', 0),
        hit=round(sum(1 for x in net if x[2] == 'TARGET') / n, 4),
        gross_points=round(sum(x[3] for x in net) / n / 4.0, 3),
        net_points=round(sum(x[0] for x in net) / n / 4.0, 3),
        net_r=round(sum(x[0] / x[1] for x in net) / n, 4),
        mean_risk_points=round(sum(x[1] for x in net) / n / 4.0, 2),
        outcomes=dict(collections.Counter(x[2] for x in net)),
        t=st.get('t'), p=st.get('p'),
        ci95_net_ticks=st.get('ci95'),
        by_session={s: round(v / 4.0, 2) for s, v in sorted(
            _sum_by(cl).items())})


def _sum_by(cl):
    out = collections.defaultdict(float)
    for s, x, _e, _v in cl:
        out[s] += x
    return out


def table(scored, cuts, keep=None):
    """{instrument: [test dicts]} with Holm over the five on NQ."""
    insts = sorted({e['instrument'] for rows in scored.values()
                    for e, *_x in rows})
    out = {}
    for inst in insts:
        tests = []
        for tid, fam, kind in TESTS:
            rows = [x for x in scored.get(tid, []) if
                    x[0]['instrument'] == inst and
                    (keep is None or keep(x[0]['session']))]
            if kind == 'trapped':
                c = cuts.get(inst)
                rows = [] if c is None else [x for x in rows
                                             if x[0]['trapped'] >= c]
            st = test_stats(rows, inst)
            st.update(test=tid, family=fam, exit=kind)
            tests.append(st)
        rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
        for x, rj in zip(tests, rej):
            if x['n'] < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and x['net_points'] > 0 and x.get('ci95_net_ticks') and \
                    x['ci95_net_ticks'][0] > 0:
                x['status'] = 'PROMISING'
            else:
                x['status'] = 'NO SIGNAL'
        out[inst] = tests
    return out


# ---------------------------------------------------------------------
# the modes
# ---------------------------------------------------------------------
def run_dev(capture_dir, max_sessions=None):
    r = LevelBreakRunner(capture_dir, max_sessions=max_sessions)
    led = r.run()
    ev = level_events(r)
    sc = score_events(r, ev)
    insts = sorted({e['instrument'] for e in ev})
    cuts = {i: trapped_cut(ev, i) for i in insts}
    rep = dict(wave6=W6_VERSION, registration=REGISTRATION, mode='dev',
               note='DEV sessions were seen before this registration: '
                    'these numbers describe, they do not test',
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               events=dict(collections.Counter((e['instrument'], e['family'])
                                               for e in ev).items()),
               trapped_cut=cuts, tests=table(sc, cuts))
    rep['events'] = {'%s %s' % k: v for k, v in rep['events'].items()}
    frozen = dict(wave6=W6_VERSION, registration=REGISTRATION,
                  trapped_cut=cuts,
                  rule='trapped cut = the median trapped volume of the DEV '
                       'L2 events per instrument, fixed by registration A4')
    return rep, frozen, r


def run_evaluate(capture_dir, frozen, unblind=False, holdout=False,
                 max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = LevelBreakRunner(capture_dir, unblind=unblind, holdout=holdout,
                         max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s)' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s), a reproduction check' % DEV_END
    ev = level_events(r)
    sc = score_events(r, ev)
    tab = table(sc, frozen.get('trapped_cut', {}), keep)
    final = unblind or holdout
    for tests in tab.values():
        for x in tests:
            if not final:
                x['status'] += ' (DEV reproduction, not a verdict)'
    rep = dict(wave6=W6_VERSION, registration=REGISTRATION, mode='evaluate',
               evaluated_on=which, unblind=unblind, holdout=holdout,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev
                                          if keep(e['session'])}),
               trapped_cut=frozen.get('trapped_cut'), tests=tab)
    return rep, r


def record_holdout_read(rep, path):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=W6_VERSION, sessions=rep['sessions_inspected']))
    old['rule'] = ('Replay holdout sessions are read once by each '
                   'registered wave; a later read of NEW rules on them is '
                   'not a fresh test.')
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def text(rep):
    lines = ['%s  %s  %s' % (rep['wave6'], rep['mode'],
                             rep.get('evaluated_on', '')),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-')]
    if rep.get('note'):
        lines.append('NOTE: ' + rep['note'])
    lines.append('trapped-volume cut (contracts): %s' % rep['trapped_cut'])
    lines.append('target 25 pts, 30 min; net = after commission, a tick of '
                 'spread and a tick of slip on stops; R = net / risk')
    for inst, tests in rep['tests'].items():
        lines.append('')
        lines.append('%s  %-4s %-3s %-11s %5s %4s %6s %8s %8s %7s %7s %7s '
                     '%8s  %s' % (inst, 'test', 'pat', 'exit', 'n', 'ses',
                                  'hit', 'gross', 'net', 'R', 'risk', 't',
                                  'p', 'status'))
        for x in tests:
            if not x['n']:
                lines.append('     %-4s %-3s %-11s     0' % (
                    x['test'], x['family'], x['exit']))
                continue
            lines.append('     %-4s %-3s %-11s %5d %4d %6.3f %+8.2f %+8.2f '
                         '%+7.3f %7.2f %7s %8s  %s' % (
                             x['test'], x['family'], x['exit'], x['n'],
                             x['sessions'], x['hit'], x['gross_points'],
                             x['net_points'], x['net_r'],
                             x['mean_risk_points'],
                             '-' if x.get('t') is None else '%.2f' % x['t'],
                             '-' if x.get('p') is None else '%.4f' % x['p'],
                             x['status']))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    ev = arg('--evaluate')
    if (unblind or holdout) and not ev:
        print('REFUSED: --unblind and --holdout are only for --evaluate with '
              'the frozen file. A plain run reads DEV sessions only.')
        return 2
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    try:
        if ev:
            try:
                frozen = json.load(open(ev))
                frozen['trapped_cut']
            except (OSError, ValueError, KeyError, TypeError):
                print('STOPPED: %s is not a wave-six frozen file (the '
                      '--frozen-out of the DEV run)' % ev)
                return 2
            if unblind or holdout:
                print('*** %s: this read scores the five registered tests '
                      'once. ***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
            rep, _r = run_evaluate(d, frozen, unblind, holdout, ms)
        else:
            rep, frozen, _r = run_dev(d, ms)
            fo = arg('--frozen-out')
            if fo:
                json.dump(frozen, open(fo, 'w'), indent=1)
                print('frozen trapped-volume cut -> %s' % fo)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-six report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if ev and unblind:
        n = _expose(rep, os.path.join(here, 'MROF_EXPOSED_PILOT_DEV_DAYS.json'))
        print('exposure ledger -> %d days' % n)
    if ev and holdout:
        n = record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER))
        print('replay holdout read recorded (%d read(s))' % n)
    return 0


def _expose(rep, path):
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    for s in rep['sessions_inspected']:
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=PI.EXPOSURE_LABEL,
                         exposed_by=W6_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W6_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W6_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W6_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded, which is permanent.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


if __name__ == '__main__':
    sys.exit(main())
