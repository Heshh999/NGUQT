#!/usr/bin/env python3
"""mrofyt_obviouslevels.py - MROF-YT-W15-OBVIOUSLEVELS-1.0

MROF_YT_WAVE15_OBVIOUSLEVELS_REGISTRATION.md turned into running code:
L2's 10-second analogue (wave eleven's WICK entry) at three groups of
levels many traders watch, each judged alone:

    IB      the 09:30-10:30 ET high and low (initial balance)
    ROUND   every 100 points
    EQUAL   equal highs and lows: two 15-minute swings within 1 point

Only the first signal at each level per session; target 25 points, stop
15, 30 minutes, one position at a time per group, net of costs. NQ:
PASS needs 30+ trades, Holm over the three groups, the 95 % interval
above 0 and a profit without the best day. A held-out read shows only
the count for a group under 30 trades.

    python3 mrofyt_obviouslevels.py "<capture>" --out w15.json             # DEV: describes
    python3 mrofyt_obviouslevels.py "<capture>" --unblind --out w15_eval.json   # secondary test
    python3 mrofyt_obviouslevels.py "<replay folder>" --holdout --out w15_replay.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_earlylevels as E
import mrofyt_l2firstsignal as FS
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W15_VERSION = 'MROF-YT-W15-OBVIOUSLEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE15_OBVIOUSLEVELS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK

GROUPS = ('IB', 'ROUND', 'EQUAL')
GROUP_NAMES = dict(IB='IB: the 09:30-10:30 high and low',
                   ROUND='ROUND: every 100 points',
                   EQUAL='EQUAL: equal highs and lows')
IB_FROM, IB_TO = 9.5 * 3600, 10.5 * 3600
IB_UNTIL = 17.0 * 3600
IB_EDGE_S = 60.0
IB_GAP_S = 120.0
ROUND_STEP = 100.0
EQ_CANDLE_S = 900
EQ_TOL_TICKS = 4
EQ_MERGE_TICKS = 2
EQ_SESSIONS = E.SWING_SESSIONS
MIN_TRADES = FS.MIN_TRADES
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


class ObviousLevelsRunner(FS.FirstSignalRunner):
    """Wave fourteen's runner (wave eight's), unchanged; the ledger names
    wave fifteen. The levels are built after the read from the mids."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        FS.FirstSignalRunner.__init__(self, capture_dir, unblind=unblind,
                                      holdout=holdout, **kw)
        self.ledger['wave15'] = dict(version=W15_VERSION)


# ---------------------------------------------------------------------
# registration 1: the levels
# ---------------------------------------------------------------------
def scan(paths):
    """One pass over one instrument's time-ordered mid paths: its
    15-minute candles {k: [high, low, close, last time]} and its
    initial-balance windows {Eastern day: dict}."""
    c15, ib = {}, {}
    for ts, ps in paths:
        for t, p in zip(ts, ps):
            loc = t + E.et_offset_hourly(t)
            k = int(loc // EQ_CANDLE_S)
            c = c15.get(k)
            if c is None:
                c15[k] = [p, p, p, t]
            else:
                if p > c[0]:
                    c[0] = p
                if p < c[1]:
                    c[1] = p
                c[2], c[3] = p, t
            sod = loc % 86400.0
            if IB_FROM <= sod < IB_TO:
                day = int(loc // 86400)
                w = ib.get(day)
                if w is None:
                    ib[day] = dict(first=sod, last=sod, prev=t, gap=0.0,
                                   hi=p, lo=p, t=t)
                else:
                    if t - w['prev'] > w['gap']:
                        w['gap'] = t - w['prev']
                    w['prev'], w['last'] = t, sod
                    if p > w['hi']:
                        w['hi'] = p
                    if p < w['lo']:
                        w['lo'] = p
    return c15, ib


def ib_levels(ib):
    """IB_HIGH and IB_LOW of every session whose window the recording
    covers (registration 1.1), known 10:30 ET to 17:00 ET."""
    out = []
    for day, w in sorted(ib.items()):
        if w['first'] > IB_FROM + IB_EDGE_S or \
                w['last'] < IB_TO - IB_EDGE_S or w['gap'] > IB_GAP_S:
            continue
        t930 = day * 86400.0 + IB_FROM - E.et_offset_hourly(w['t'])
        ses = RUN.session_id(w['t'])
        for kind, px in (('IB_HIGH', w['hi']), ('IB_LOW', w['lo'])):
            out.append(dict(id='%s@%s' % (kind, ses), kind=kind, group='IB',
                            price=px, t_on=t930 + (IB_TO - IB_FROM),
                            t_off=t930 + (IB_UNTIL - IB_FROM), session=ses))
    return out


def round_levels(grid):
    """Every multiple of 100 points between a session's lowest and
    highest grid mid, one step beyond each, for that session."""
    by = {}
    for g in grid:
        m = g.get('mid')
        if m is None:
            continue
        b = by.get(g['session'])
        if b is None:
            by[g['session']] = [m, m, g['t'], g['t']]
        else:
            b[0], b[1] = min(b[0], m), max(b[1], m)
            b[2], b[3] = min(b[2], g['t']), max(b[3], g['t'])
    out = []
    for ses, (lo, hi, t0, t1) in sorted(by.items()):
        for k in range(int(math.floor(lo / ROUND_STEP)) - 1,
                       int(math.ceil(hi / ROUND_STEP)) + 2):
            px = k * ROUND_STEP
            out.append(dict(id='R%d@%s' % (int(px), ses), kind='ROUND',
                            group='ROUND', price=float(px), t_on=t0,
                            t_off=t1 + 1.0, session=ses))
    return out


def _end15(k, t_ref):
    return float((k + 1) * EQ_CANDLE_S - E.et_offset_hourly(t_ref))


def swings15(cands):
    """Wave eleven's swing rule on 15-minute candles: a high above the 2
    before and not below the 2 after over five consecutive recorded
    candles (lows mirrored), confirmed at the close of the 2nd after;
    standing until a later candle closes a tick beyond it."""
    S = E.SWING_SIDE
    ks = sorted(cands)
    out = []
    for i in range(S, len(ks) - S):
        k = ks[i]
        if ks[i - S:i + S + 1] != list(range(k - S, k + S + 1)):
            continue
        h, lo = cands[k][0], cands[k][1]
        before = [cands[k - j] for j in range(1, S + 1)]
        after = [cands[k + j] for j in range(1, S + 1)]
        t_on = _end15(k + S, cands[k + S][3])
        for kind, px, ok, beyond in (
                ('SWING_H', h, h > max(c[0] for c in before) and
                 h >= max(c[0] for c in after),
                 lambda c, px=h: c[2] >= px + TICK - 1e-9),
                ('SWING_L', lo, lo < min(c[1] for c in before) and
                 lo <= min(c[1] for c in after),
                 lambda c, px=lo: c[2] <= px - TICK + 1e-9)):
            if not ok:
                continue
            t_off = float('inf')
            for k2 in ks[i + S + 1:]:
                if beyond(cands[k2]):
                    t_off = _end15(k2, cands[k2][3])
                    break
            out.append(dict(kind=kind, price=px, t_on=t_on, t_off=t_off,
                            session=RUN.session_id(t_on)))
    return out


def equal_levels(swings, ses_index):
    """EQ_HIGH / EQ_LOW levels (registration 1.2)."""
    out = []
    for kind, d, tag in (('SWING_H', 1, 'EQ_HIGH'),
                         ('SWING_L', -1, 'EQ_LOW')):
        lst = sorted((s for s in swings if s['kind'] == kind),
                     key=lambda s: s['t_on'])
        for j, s2 in enumerate(lst):
            si2 = ses_index.get(s2['session'])
            if si2 is None:
                continue
            match = [s1 for s1 in lst[:j]
                     if s1['t_on'] < s2['t_on'] < s1['t_off'] and
                     ses_index.get(s1['session'], -10 ** 9) >=
                     si2 - EQ_SESSIONS and
                     abs(s1['price'] - s2['price']) <=
                     EQ_TOL_TICKS * TICK + 1e-9]
            if not match:
                continue
            s1 = match[-1]
            src = s1 if d * (s1['price'] - s2['price']) > 0 else s2
            px = src['price']
            if any(lv['kind'] == tag and
                   lv['t_on'] <= s2['t_on'] < lv['t_off'] and
                   ses_index.get(lv['session'], -10 ** 9) >=
                   si2 - EQ_SESSIONS and
                   abs(lv['price'] - px) <= EQ_MERGE_TICKS * TICK + 1e-9
                   for lv in out):
                continue
            out.append(dict(id='%s#%d' % (tag, len(out) + 1), kind=tag,
                            group='EQUAL', price=px, t_on=s2['t_on'],
                            t_off=src['t_off'], session=s2['session']))
    return out


def levels_by_instrument(r):
    """{instrument: [level dicts with ses_idx]} for the three groups."""
    paths = collections.defaultdict(list)
    for (inst, _run), path in V.compressed_paths(r).items():
        paths[inst].append(path)
    grid = collections.defaultdict(list)
    for g in r.grid:
        grid[g['instrument']].append(g)
    out = {}
    for inst in sorted(set(paths) | set(grid)):
        ps = sorted(paths.get(inst, []), key=lambda p: p[0][0])
        ses_list = sorted({g['session'] for g in grid.get(inst, [])})
        ses_index = {s: i for i, s in enumerate(ses_list)}
        c15, ib = scan(ps)
        lv = (ib_levels(ib) + round_levels(grid.get(inst, [])) +
              equal_levels(swings15(c15), ses_index))
        for x in lv:
            x['ses_idx'] = bisect.bisect_left(ses_list, x['session'])
        out[inst] = lv
    return out


# ---------------------------------------------------------------------
# registration 2: the signal
# ---------------------------------------------------------------------
def wick_events(r, levels):
    """Wave eleven's WICK entries at these levels only, per run."""
    runs = collections.defaultdict(list)
    sessions = collections.defaultdict(set)
    for g in r.grid:
        runs[(g['instrument'], g['run'])].append(g)
        sessions[g['instrument']].add(g['session'])
    order = sorted(runs, key=lambda k: (k[0], min(g['t'] for g in runs[k])))
    counts = collections.Counter()
    out = []
    for key in order:
        inst = key[0]
        grid = sorted(runs[key], key=lambda g: g['t'])
        # only these levels: none of wave eleven's fixed ones
        light = [dict(t=g['t'], mid=g.get('mid'), D=g.get('D'),
                      z_delta_s=g.get('z_delta_s'), instrument=inst,
                      session=g['session'], run=g['run']) for g in grid]
        ses_index = {s: i for i, s in enumerate(sorted(sessions[inst]))}
        t0, t1 = grid[0]['t'], grid[-1]['t']
        lv = [x for x in levels.get(inst, [])
              if x['t_on'] <= t1 and x['t_off'] > t0]
        group_of = {x['id']: x['group'] for x in lv}
        for e in E.run_episodes(light, {}, lv, ses_index, counts, 'WICK'):
            e['group'] = group_of[e['level_id']]
            out.append(e)
    return out


def first_signals(events):
    """The first signal at each level per instrument and session."""
    seen, out = set(), []
    for e in sorted(events, key=lambda e: (e['instrument'], e['session'],
                                           e['t'])):
        k = (e['instrument'], e['session'], e['level_id'])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


def score(r, events):
    """[(event, outcome, gross ticks, risk ticks, seconds)]: target 100
    ticks, stop 60, 1 800 s on the event's run path (wave six's
    path_exit); a trade its run ends before is dropped."""
    paths = V.compressed_paths(r)
    out = []
    for e in events:
        key = (e['instrument'], e['run'])
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        res = LB.path_exit(ts, ps, i, e['direction'], LB.TARGET,
                           LB.FIXED_STOP)
        if res[0] != 'UNRESOLVED':
            out.append((e, res[0], res[1], LB.FIXED_STOP, res[2]))
    return out


# ---------------------------------------------------------------------
# registration 3: the verdicts
# ---------------------------------------------------------------------
def group_verdicts(rows_of):
    """rows_of: {group: one instrument's trades, one at a time}. Wave
    fourteen's verdict per group, then Holm over the three on NQ."""
    out = {}
    for grp in GROUPS:
        out[grp] = FS.verdict(rows_of.get(grp, []), rows_of.get('_inst'))
    if rows_of.get('_inst') != PRIMARY:
        return out
    ps = [out[g].get('p') if out[g]['n'] >= MIN_TRADES else None
          for g in GROUPS]
    rej = BM.holm(ps, HOLM_ALPHA)
    for g, rj in zip(GROUPS, rej):
        x = out[g]
        x['holm_rejected'] = rj
        if x['n'] >= MIN_TRADES and not rj:
            x['status'] = 'NOT PROVEN'
            if not any('luck' in m for m in x['reasons']):
                x['reasons'] = x['reasons'] + [
                    'could be luck after allowing for three groups (Holm)']
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = ObviousLevelsRunner(capture_dir, unblind=unblind, holdout=holdout,
                            max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s): secondary test' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    levels = levels_by_instrument(r)
    ev = [e for e in wick_events(r, levels) if keep(e['session'])]
    first_ids = {id(e) for e in first_signals(ev)}
    scored = score(r, ev)
    insts = sorted({e['instrument'] for e in ev} | {PRIMARY})
    groups = {g: {} for g in GROUPS}
    for inst in insts:
        mine = lambda g, firsts: V.one_at_a_time(   # noqa: E731
            [x for x in scored if x[0]['instrument'] == inst and
             x[0]['group'] == g and (not firsts or id(x[0]) in first_ids)])
        rows_of = dict((g, mine(g, True)) for g in GROUPS)
        rows_of['_inst'] = inst
        ver = group_verdicts(rows_of)
        for g in GROUPS:
            b = LB.test_stats(mine(g, False), inst)
            groups[g][inst] = dict(test=ver[g], every=dict(
                n=b['n'], sessions=b.get('sessions', 0), hit=b.get('hit'),
                net_points=b.get('net_points')))
    withheld = []
    for g in GROUPS:
        if (unblind or holdout) and \
                groups[g][PRIMARY]['test']['n'] < MIN_TRADES:
            withheld.append(g)
            for inst in groups[g]:
                x = FS._withhold(groups[g][inst]['test'])
                x['status'] = (
                    'NOT ENOUGH TRADES: results withheld until a read holds '
                    '%d' % MIN_TRADES if inst == PRIMARY else 'withheld')
                groups[g][inst] = dict(test=x)
        elif not (unblind or holdout):
            for inst in groups[g]:
                groups[g][inst]['test']['status'] += \
                    ' (DEV, seen before the registration)'
    rep = dict(wave15=W15_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, min_trades=MIN_TRADES,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev}),
               levels=dict((inst, dict(collections.Counter(
                   x['group'] for x in lv if keep(x['session']))))
                   for inst, lv in levels.items()),
               groups=groups)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave15'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'levels built: %s' % ('; '.join(
                 '%s %s' % (inst, ', '.join('%s %d' % (g, c.get(g, 0))
                                            for g in GROUPS))
                 for inst, c in sorted(rep['levels'].items())) or '-'),
             'rule: the first 10 s L2-style signal (WICK) at each level per '
             'session; target 25 pts, stop 15 pts, 30 min; one trade at a '
             'time per group; net after costs']
    for g in GROUPS:
        for inst, res in sorted(rep['groups'][g].items(),
                                key=lambda kv: kv[0] != PRIMARY):
            x = res['test']
            lines.append('')
            lines.append('%s  %s%s' % (inst, GROUP_NAMES[g],
                                       ' (tested)' if inst == PRIMARY
                                       else ''))
            lines.append('   trades %d over %d days' % (
                x['n'], x.get('sessions', 0)))
            if g in rep['withheld']:
                lines.append('   %s' % x['status'])
                continue
            if x['n']:
                ci = x.get('ci95_net_ticks')
                lines.append('   won %.0f%%, net %s a trade, total %s points'
                             % (100 * x['hit'], _pts(x['net_points']),
                                _pts(x.get('total_net_points'))))
                lines.append('   95%% range of net a trade: %s   p %s' % (
                    '-' if not ci else '%s .. %s points' % (
                        _pts(ci[0] / 4.0), _pts(ci[1] / 4.0)),
                    '-' if x.get('p') is None else '%.4f' % x['p']))
                wb = x['without_best_day']
                lines.append('   without the best day (%s): %d trades, net '
                             '%s a trade' % (wb['session'], wb['n'],
                                             _pts(wb['net_points'])))
            lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
                x['reasons'])) if x.get('reasons') else ''))
            b = res['every']
            lines.append('   beside, not tested: every signal %d trades, %s, '
                         'net %s a trade' % (
                             b['n'], '-' if not b['n'] else
                             'won %.0f%%' % (100 * b['hit']),
                             _pts(b['net_points'])))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def record_holdout_read(rep, path):
    return LG.record_holdout_read(rep, path, W15_VERSION)


def record_exposure(rep, path):
    return LG.record_exposure(rep, path, W15_VERSION)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    if unblind or holdout:
        print('*** %s: this read is the registered test of the three '
              'obvious-level groups. ***\n' % ('UNBLIND' if unblind
                                              else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-fifteen report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER))
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER))
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
