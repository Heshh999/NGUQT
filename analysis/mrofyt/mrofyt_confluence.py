#!/usr/bin/env python3
"""mrofyt_confluence.py - MROF-YT-W17-CONFLUENCE-1.0

MROF_YT_WAVE17_CONFLUENCE_REGISTRATION.md turned into running code: the
10-second L2 analogue (wave eleven's WICK entry) at every level of every
family, graded by how many level families sit within 2 points of it:

    A+   3 or more families in the zone
    A    2 families
    B    1 (no confluence)

    C1  confluence (A+ and A) minus B, FIXED 25 / 15      session-clustered
    C2  A+ minus A, FIXED
    C3  confluence: WIDE (40 / 15) minus FIXED, paired
    C4  confluence trades make money (wave fourteen's verdict)
    Holm over four on NQ; the 1 / 2 / 3 contract sizing ladder described

    python3 mrofyt_confluence.py "<capture>" --out w17.json               # DEV: describes
    python3 mrofyt_confluence.py "<capture>" --unblind --out w17_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import os
import re
import sys

import mrofyt_bigmove as BM
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_earlylevels as E
import mrofyt_l2firstsignal as FS
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_obviouslevels as OL
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG
import mrofyt_smt as SMT
import mrofyt_valuearea as VA

W17_VERSION = 'MROF-YT-W17-CONFLUENCE-1.0'
REGISTRATION = 'MROF_YT_WAVE17_CONFLUENCE_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK

ZONE_TICKS = 8
CLUSTER_S = 60.0
WIDE_TARGET = 160
GRADES = ('A+', 'A', 'B')
LADDER = {'A+': 3, 'A': 2, 'B': 1}
MIN_TRADES = FS.MIN_TRADES
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT

FIXED_FAMILY = dict(
    YDAY_HIGH='YDAY', YDAY_LOW='YDAY', OVERNIGHT_HIGH='OVERNIGHT',
    OVERNIGHT_LOW='OVERNIGHT', LWEEK_HIGH='LWEEK', LWEEK_LOW='LWEEK',
    CASH_OPEN_0930='CASH_OPEN', GLOBEX_OPEN='GLOBEX_OPEN',
    SESSION_VWAP='VWAP', VWAP_UPPER='VWAP', VWAP_LOWER='VWAP',
    PP='PIVOT', R1='PIVOT', S1='PIVOT', M2='PIVOT', M3='PIVOT')
_SWING = re.compile(r'^SWING_[HL]_(\d)H@')


class ConfluenceRunner(VA.ValueRunner):
    """Wave thirteen's runner (every wave's hooks), unchanged; the ledger
    names wave seventeen."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        VA.ValueRunner.__init__(self, capture_dir, unblind=unblind,
                                holdout=holdout, **kw)
        self.ledger['wave17'] = dict(version=W17_VERSION)


# ---------------------------------------------------------------------
# registration 1: the levels and their families
# ---------------------------------------------------------------------
def family_of(level_id):
    if level_id in FIXED_FAMILY:
        return FIXED_FAMILY[level_id]
    m = _SWING.match(level_id)
    if m:
        return 'SWING_%sH' % m.group(1)
    if level_id.startswith('IB_'):
        return 'IB'
    if level_id.startswith('EQ_'):
        return 'EQUAL'
    if level_id.startswith('VA_'):
        return 'VALUE'
    if level_id.startswith('R') and '@' in level_id:
        return 'ROUND'
    return 'OTHER'


def value_levels(r, grid_of):
    """Yesterday's cash-session POC, VAH and VAL for each session that has
    them, known for the whole session."""
    out = collections.defaultdict(list)
    for inst, grid in grid_of.items():
        span = {}
        for g in grid:
            s = span.setdefault(g['session'], [g['t'], g['t']])
            s[0], s[1] = min(s[0], g['t']), max(s[1], g['t'])
        for ses, (t0, t1) in sorted(span.items()):
            va = VA.prev_value(r.values.get(inst, {}), ses)
            if va is None:
                continue
            for name, px in zip(('POC', 'VAH', 'VAL'), va):
                out[inst].append(dict(id='VA_%s@%s' % (name, ses),
                                      price=px, t_on=t0, t_off=t1 + 1.0,
                                      session=ses))
    return out


def all_levels(r):
    """{instrument: [listed level dicts with ses_idx]}: the swings, the
    obvious levels and yesterday's value area. The fixed levels travel on
    the grid records (wave eleven's copy)."""
    grid_of = collections.defaultdict(list)
    for g in r.grid:
        grid_of[g['instrument']].append(g)
    swings = E.swings_by_instrument(r)
    obvious = OL.levels_by_instrument(r)
    values = value_levels(r, grid_of)
    out = {}
    for inst in sorted(grid_of):
        ses_list = sorted({g['session'] for g in grid_of[inst]})
        lv = list(swings.get(inst, [])) + list(values.get(inst, []))
        for x in lv:
            x['ses_idx'] = bisect.bisect_left(ses_list, x['session'])
        out[inst] = lv + list(obvious.get(inst, []))
    return out


# ---------------------------------------------------------------------
# registration 2-3: the signal, the event and its grade
# ---------------------------------------------------------------------
def grade_of(n_families):
    return 'A+' if n_families >= 3 else ('A' if n_families == 2 else 'B')


def zone_families(g, listed, ses_index, fired_prices):
    """The families with a level known at grid record g within 8 ticks of
    any fired level."""
    out = set()
    for _key, lid, _grp, px in E._levels_at(g, listed, ses_index):
        if px is None:
            continue
        if any(abs(px - L) <= ZONE_TICKS * TICK + 1e-9 for L in fired_prices):
            out.add(family_of(lid))
    return out


def cluster(sigs):
    """Signals of one instrument, time-ordered, into events: the same
    direction within 60 s of the event's first signal."""
    events, open_ = [], {}
    for s in sigs:
        cur = open_.get(s['direction'])
        if cur is not None and s['t'] - cur[0]['t'] <= CLUSTER_S + 1e-9:
            cur.append(s)
            continue
        cur = [s]
        open_[s['direction']] = cur
        events.append(cur)
    return events


def events(r, levels=None):
    """Every graded event of the read: the first signal at each level per
    session, collapsed within 60 s, graded at the first signal."""
    levels = all_levels(r) if levels is None else levels
    runs = collections.defaultdict(list)
    sessions = collections.defaultdict(set)
    for g in r.grid:
        runs[(g['instrument'], g['run'])].append(g)
        sessions[g['instrument']].add(g['session'])
    order = sorted(runs, key=lambda k: (k[0], min(g['t'] for g in runs[k])))
    counts = collections.Counter()
    seen = set()
    out = []
    for key in order:
        inst = key[0]
        grid = sorted(runs[key], key=lambda g: g['t'])
        gmap = {int(round(g['t'])): g for g in grid}
        ses_index = {s: i for i, s in enumerate(sorted(sessions[inst]))}
        t0, t1 = grid[0]['t'], grid[-1]['t']
        listed = [x for x in levels.get(inst, [])
                  if x['t_on'] <= t1 and x['t_off'] > t0]
        sigs = []
        for s in sorted(E.run_episodes(grid, {}, listed, ses_index, counts,
                                       'WICK'), key=lambda s: s['t']):
            k = (inst, s['session'], s['level_id'])
            if k in seen:
                continue
            seen.add(k)
            sigs.append(s)
        for ev in cluster(sigs):
            first = ev[0]
            g = gmap.get(int(round(first['t'])))
            fired = [s['level'] for s in ev]
            fams = zone_families(g, listed, ses_index, fired) if g else set()
            fams |= {family_of(s['level_id']) for s in ev}
            out.append(dict(
                instrument=inst, session=first['session'], run=first['run'],
                t=first['t'], direction=first['direction'],
                level_id=first['level_id'], level=first['level'],
                fired=[s['level_id'] for s in ev],
                families=sorted(fams), grade=grade_of(len(fams))))
    return out


# ---------------------------------------------------------------------
# registration 4: the trades
# ---------------------------------------------------------------------
def net_points(inst, outcome, gross_ticks):
    return (gross_ticks - CO.cost_ticks(
        inst, 'STOP' if outcome == 'STOP' else 'TARGET')) * TICK


def score(r, evs):
    """[(event, outcome, gross ticks, risk ticks, seconds)] on FIXED, each
    event carrying its WIDE result; dropped when either is unresolved."""
    paths = V.compressed_paths(r)
    out = []
    for e in evs:
        key = (e['instrument'], e['run'])
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        fx = LB.path_exit(ts, ps, i, e['direction'], LB.TARGET,
                          LB.FIXED_STOP)
        wd = LB.path_exit(ts, ps, i, e['direction'], WIDE_TARGET,
                          LB.FIXED_STOP)
        if fx[0] == 'UNRESOLVED' or wd[0] == 'UNRESOLVED':
            continue
        e = dict(e, fixed_net=net_points(e['instrument'], fx[0], fx[1]),
                 wide_net=net_points(e['instrument'], wd[0], wd[1]),
                 wide_outcome=wd[0])
        out.append((e, fx[0], fx[1], LB.FIXED_STOP, fx[2]))
    return out


# ---------------------------------------------------------------------
# registration 5-6: the tests and the ladder
# ---------------------------------------------------------------------
def _side(rows):
    return [(x[0]['session'], x[0]['fixed_net']) for x in rows]


def tests(rows, inst):
    """rows: one instrument's trades, one at a time. C1-C4 with Holm."""
    by = {g: [x for x in rows if x[0]['grade'] == g] for g in GRADES}
    conf = by['A+'] + by['A']
    c1 = SMT.diff_stats(_side(conf), _side(by['B']))
    c2 = SMT.diff_stats(_side(by['A+']), _side(by['A']))
    d3 = [(x[0]['session'], x[0]['wide_net'] - x[0]['fixed_net'])
          for x in conf]
    s3 = DI.cluster_stats([(s, v, 0.0, v) for s, v in d3])
    c4 = FS.verdict(conf, inst)
    out = [
        dict(test='C1', name='confluence minus no confluence',
             n=min(len(conf), len(by['B'])), n_a=len(conf), n_b=len(by['B']),
             effect=c1.get('diff'), ci95=c1.get('ci95'), p=c1.get('p')),
        dict(test='C2', name='A+ minus A',
             n=min(len(by['A+']), len(by['A'])), n_a=len(by['A+']),
             n_b=len(by['A']), effect=c2.get('diff'), ci95=c2.get('ci95'),
             p=c2.get('p')),
        dict(test='C3', name='confluence: 40-point target minus 25',
             n=len(conf), effect=s3.get('lift'), ci95=s3.get('ci95'),
             p=s3.get('p')),
        dict(test='C4', name='confluence trades make money',
             n=len(conf), effect=c4.get('net_points'),
             ci95=(None if not c4.get('ci95_net_ticks') else
                   tuple(v * TICK for v in c4['ci95_net_ticks'])),
             p=c4.get('p'), verdict14=c4.get('status'),
             reasons14=c4.get('reasons', []))]
    if inst != PRIMARY:
        for x in out:
            x['status'], x['reasons'] = 'DESCRIBED (not tested)', []
        return out
    rej = BM.holm([x['p'] if x['n'] >= MIN_TRADES else None for x in out],
                  HOLM_ALPHA)
    for x, rj in zip(out, rej):
        if x['n'] < MIN_TRADES:
            x['status'], x['reasons'] = 'NOT ENOUGH TRADES', [
                '%d of the %d needed%s' % (
                    x['n'], MIN_TRADES, ' on each side' if 'n_b' in x
                    else '')]
            continue
        reasons = []
        if x['effect'] is None or x['effect'] <= 0:
            reasons.append('no better' if x['test'] != 'C4'
                           else 'loses after costs')
        elif not x['ci95'] or x['ci95'][0] <= 0:
            reasons.append('could be luck: the 95 % range reaches zero')
        elif not rj:
            reasons.append('could be luck after allowing for four tests '
                           '(Holm)')
        if x['test'] == 'C4' and not reasons and x['verdict14'] != 'PASS':
            reasons += x['reasons14'] or ['wave fourteen\'s verdict fails']
        x['status'] = 'NOT PROVEN' if reasons else 'PASS'
        x['reasons'] = reasons
    return out


def ladder(rows):
    """The 1 / 2 / 3 contract ladder against 1 contract, one at a time."""
    def run_of(size):
        tot = peak = dd = 0.0
        ctr = 0
        for x in rows:
            c = size(x[0]['grade'])
            tot += c * x[0]['fixed_net']
            ctr += c
            peak = max(peak, tot)
            dd = min(dd, tot - peak)
        return dict(total_points=round(tot, 2), contracts=ctr,
                    per_contract=round(tot / ctr, 3) if ctr else None,
                    max_drawdown=round(dd, 2))
    return dict(flat=run_of(lambda g: 1),
                ladder=run_of(lambda g: LADDER[g]))


def describe(rows, all_events):
    by = {}
    for g in GRADES:
        v = [x[0] for x in rows if x[0]['grade'] == g]
        by[g] = dict(n=len(v),
                     fixed_net=round(sum(e['fixed_net'] for e in v) / len(v),
                                     3) if v else None,
                     wide_net=round(sum(e['wide_net'] for e in v) / len(v),
                                    3) if v else None,
                     won=round(sum(1 for x in rows if x[0]['grade'] == g and
                                   x[1] == 'TARGET') / len(v), 4)
                     if v else None)
    zones = collections.Counter(
        '+'.join(e['families']) for e in all_events if e['grade'] == 'A+')
    return dict(by_grade=by, events_by_grade=dict(collections.Counter(
        e['grade'] for e in all_events)),
        top_aplus_zones=zones.most_common(5))


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
_KEEP = ('test', 'name', 'n', 'n_a', 'n_b', 'status')


def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = ConfluenceRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    evs = [e for e in events(r) if keep(e['session'])]
    scored = score(r, evs)
    insts = sorted({e['instrument'] for e in evs} | {PRIMARY})
    results = {}
    for inst in insts:
        rows = V.one_at_a_time([x for x in scored
                                if x[0]['instrument'] == inst])
        mine = [e for e in evs if e['instrument'] == inst]
        res = dict(tests=tests(rows, inst), ladder=ladder(rows),
                   describe=describe(rows, mine))
        results[inst] = res
    final = unblind or holdout
    withheld = []
    if final:
        nq = results[PRIMARY]['tests']
        withheld = [x['test'] for x in nq if x['n'] < MIN_TRADES]
        c1_short = 'C1' in withheld
        for inst, res in results.items():
            for i, x in enumerate(res['tests']):
                if x['test'] in withheld:
                    res['tests'][i] = dict((k, x[k]) for k in _KEEP if k in x)
                    res['tests'][i]['status'] = (
                        'NOT ENOUGH TRADES: results withheld until a read '
                        'holds %d' % MIN_TRADES if inst == PRIMARY
                        else 'withheld')
            if c1_short:
                res['ladder'] = 'withheld'
                res['describe'] = dict(events_by_grade=res['describe'][
                    'events_by_grade'])
    else:
        for res in results.values():
            for x in res['tests']:
                x['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave17=W17_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in evs}),
               results=results)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave17'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'signal: the first 10 s L2-style signal (WICK) at each level of '
             'every family per session, signals within 60 s one event; A+ = '
             '3+ families within 2 points, A = 2, B = 1; FIXED 25 / 15, WIDE '
             '40 / 15, 30 min; one at a time; net after costs']
    for inst, res in sorted(rep['results'].items(),
                            key=lambda kv: kv[0] != PRIMARY):
        d = res['describe']
        lines.append('')
        lines.append('%s  CONFLUENCE%s   events: %s' % (
            inst, ' (tested)' if inst == PRIMARY else '',
            ', '.join('%s %d' % (g, d['events_by_grade'].get(g, 0))
                      for g in GRADES)))
        if 'by_grade' in d:
            for g in GRADES:
                v = d['by_grade'][g]
                lines.append('   %-3s %4d trades  won %s  net %s a trade '
                             '(40-pt target %s)' % (
                                 g, v['n'], '-' if v['won'] is None else
                                 '%.0f%%' % (100 * v['won']),
                                 _pts(v['fixed_net']), _pts(v['wide_net'])))
        for x in res['tests']:
            if 'effect' in x:
                ci = x.get('ci95')
                lines.append('   %s %-38s n %3d  %s  95%% %s  p %s -> %s%s' % (
                    x['test'], x['name'], x['n'], _pts(x['effect']),
                    '-' if not ci else '%s..%s' % (_pts(ci[0]), _pts(ci[1])),
                    '-' if x.get('p') is None else '%.4f' % x['p'],
                    x['status'], (': ' + '; '.join(x['reasons']))
                    if x.get('reasons') else ''))
            else:
                lines.append('   %s %-38s n %3d  %s' % (
                    x['test'], x['name'], x['n'], x['status']))
        lad = res['ladder']
        if isinstance(lad, dict):
            for k, name in (('flat', '1 contract always'),
                            ('ladder', 'B 1 / A 2 / A+ 3')):
                v = lad[k]
                lines.append('   sizing %-18s total %s points over %d '
                             'contracts, %s a contract, deepest drawdown %s'
                             % (name, _pts(v['total_points']),
                                v['contracts'], _pts(v['per_contract']),
                                _pts(v['max_drawdown'])))
        else:
            lines.append('   sizing: withheld')
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    if unblind or holdout:
        print('*** %s: this read is wave seventeen\'s registered test. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-seventeen report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W17_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W17_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
