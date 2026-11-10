#!/usr/bin/env python3
"""mrofyt_profilelevels.py - MROF-YT-W20-PROFILELEVELS-1.0

MROF_YT_WAVE20_PROFILELEVELS_REGISTRATION.md turned into running code:
levels of the same kind as yesterday's value area, each judged alone.

    ONVA    the overnight (18:00-09:29:59 ET) value area: POC, VAH, VAL,
            known from 09:30
    WKVA    last ISO week's value area (its cash sessions summed)
    CLOSE   yesterday's last cash-session trade (the 16:00 close)
    MID     halfway between yesterday's high and low

    ONVA WKVA CLOSE MID   the first L2-style (WICK) signal at each level
                          per session; 25 / 15 / 30 min; Holm over four
    RE-ON  RE-WK          wave thirteen's back-into-value event against
                          the overnight and the weekly value area
    NP-ALL NP-FIRST       an untested POC of the last 5 sessions, 10+
                          points ahead, as the target of an L2 trade,
                          against the fixed 25 on the same trades

NQ: PASS needs 30+ trades, the 95 % interval above 0, a result that
stands without the best day, and Holm within its family. A held-out read
shows only the count for a test under 30 trades.

    python3 mrofyt_profilelevels.py "<capture>" --out w20.json            # DEV: describes
    python3 mrofyt_profilelevels.py "<capture>" --unblind --out w20_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import datetime as _dt
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_earlylevels as E
import mrofyt_l2firstsignal as FS
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_obviouslevels as OL
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG
import mrofyt_valuearea as VA

W20_VERSION = 'MROF-YT-W20-PROFILELEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE20_PROFILELEVELS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK

ON_FROM = 18 * 3600.0                 # the overnight starts 18:00 ET
ON_LEN = 15.5 * 3600.0                # and ends 09:30 ET
ON_FIRST_X = 0.5 * 3600.0             # first trade by 18:30
ON_LAST_X = 15.0 * 3600.0             # last trade at or after 09:00
ON_UNTIL_S = 7.5 * 3600.0             # known 09:30 -> 17:00
WK_MIN_SESSIONS = 3
CLOSE_FROM = 16 * 3600.0 - 60.0       # last cash trade at or after 15:59
CLOSE_MAX_DAYS = 4
NAKED_SESSIONS = 5
NAKED_MIN_AHEAD = 40.0                # ticks: 10 points
NAKED_SHORT = 2.0                     # ticks short of the POC

GROUPS = ('ONVA', 'WKVA', 'CLOSE', 'MID')
REENTRY = ('RE-ON', 'RE-WK')
TARGETS = ('NP-ALL', 'NP-FIRST')
NAMES = collections.OrderedDict([
    ('ONVA', 'ONVA: the overnight value area (first signal)'),
    ('WKVA', 'WKVA: last week\'s value area (first signal)'),
    ('CLOSE', 'CLOSE: yesterday\'s close (first signal)'),
    ('MID', 'MID: yesterday\'s midpoint (first signal)'),
    ('RE-ON', 'RE-ON: back into the overnight value area with speed'),
    ('RE-WK', 'RE-WK: back into last week\'s value area with speed'),
    ('NP-ALL', 'NP-ALL: untested POC target minus fixed 25, every L2'),
    ('NP-FIRST', 'NP-FIRST: untested POC target minus fixed 25, first '
                 'signals')])
FAMILIES = (('levels', GROUPS, 'four level groups'),
            ('reentry', REENTRY, 'two value areas'),
            ('targets', TARGETS, 'two trade sets'))
MIN_TRADES = FS.MIN_TRADES
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT
_IH = E.FIXED_IDS.index('YDAY_HIGH')
_IL = E.FIXED_IDS.index('YDAY_LOW')


# ---------------------------------------------------------------------
# the runner: wave thirteen's, plus the overnight profile, each complete
# cash session's bins and its last cash trade
# ---------------------------------------------------------------------
class ProfileLevelsRunner(VA.ValueRunner):
    """Wave thirteen's runner. The trades it hands to its cash profile
    are also added to the session's overnight profile (18:00-09:29:59
    ET) or kept as the session's last cash trade; at the session's close
    the complete cash profile's bins and the 16:00 close are kept. Hooks
    only: nothing an earlier wave reads is touched."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        VA.ValueRunner.__init__(self, capture_dir, unblind=unblind,
                                holdout=holdout, **kw)
        self.on_prof = {}       # (inst, ses) -> [bins, first x, last x, t]
        self.cash_last = {}     # (inst, ses) -> [second of day, price]
        self.cash_bins = collections.defaultdict(dict)    # inst -> {ses: bins}
        self.cash_close = collections.defaultdict(dict)   # inst -> {ses: px}
        self.ledger['wave20'] = dict(version=W20_VERSION)

    def _add_trade(self, inst, session, t, px, sz):
        VA.ValueRunner._add_trade(self, inst, session, t, px, sz)
        if px is None or not sz or not session:
            return
        sod = (t + E.et_offset_hourly(t)) % 86400
        key = (inst, session)
        if VA.CASH_FROM <= sod < VA.CASH_TO:
            c = self.cash_last.get(key)
            if c is None or sod >= c[0]:
                self.cash_last[key] = [sod, px]
            return
        x = (sod - ON_FROM) % 86400
        if x >= ON_LEN:
            return                              # 16:00-18:00
        p = self.on_prof.get(key)
        if p is None:
            p = self.on_prof[key] = [collections.defaultdict(float), x, x, t]
        p[0][int(math.floor(px))] += sz
        if x < p[1]:
            p[1] = x
        if x >= p[2]:
            p[2], p[3] = x, t

    def _finish_profile(self, inst, session):
        p = self.profile.get((inst, session))
        if p is not None and p[1] <= VA.COMPLETE_FIRST and \
                p[2] >= VA.COMPLETE_LAST:
            self.cash_bins[inst][session] = dict(p[0])
        c = self.cash_last.pop((inst, session), None)
        if c is not None and c[0] >= CLOSE_FROM:
            self.cash_close[inst][session] = c[1]
        VA.ValueRunner._finish_profile(self, inst, session)

    def _mark_run(self, st):
        mark = VA.ValueRunner._mark_run(self, st)
        key = (st.instrument, st.session)
        p, c = self.on_prof.get(key), self.cash_last.get(key)
        mark['w20'] = (None if p is None else [dict(p[0]), p[1], p[2], p[3]],
                       None if c is None else list(c))
        return mark

    def _unwind_run(self, st, mark):
        VA.ValueRunner._unwind_run(self, st, mark)
        key = (st.instrument, st.session)
        p, c = mark['w20']
        if p is None:
            self.on_prof.pop(key, None)
        else:
            self.on_prof[key] = [collections.defaultdict(float, p[0]),
                                 p[1], p[2], p[3]]
        if c is None:
            self.cash_last.pop(key, None)
        else:
            self.cash_last[key] = list(c)


# ---------------------------------------------------------------------
# registration 1: the levels
# ---------------------------------------------------------------------
def _date(session):
    return _dt.date(int(session[:4]), int(session[4:6]), int(session[6:]))


def grid_by_instrument(r):
    out = collections.defaultdict(list)
    for g in r.grid:
        out[g['instrument']].append(g)
    return out


def on_values(r, inst):
    """{session: (POC, VAH, VAL, the 09:30 it is known from)} for every
    session whose overnight the recording covers (registration 1.1)."""
    out = {}
    for (i, ses), (bins, first_x, last_x, t_last) in r.on_prof.items():
        if i != inst or first_x > ON_FIRST_X or last_x < ON_LAST_X:
            continue
        poc, vah, val = CX.value_area(dict(bins))
        if poc is not None:
            out[ses] = (poc, vah, val, t_last + (ON_LEN - last_x))
    return out


def week_values(r, inst, sessions):
    """{session: (POC, VAH, VAL)}: the value area of the summed complete
    cash-session profiles of the ISO week before the session's."""
    by_week = collections.defaultdict(list)
    for ses, bins in sorted(r.cash_bins.get(inst, {}).items()):
        by_week[_date(ses).isocalendar()[:2]].append(bins)
    out, cache = {}, {}
    for ses in sessions:
        wk = (_date(ses) - _dt.timedelta(days=7)).isocalendar()[:2]
        if wk not in cache:
            va = None
            if len(by_week.get(wk, ())) >= WK_MIN_SESSIONS:
                tot = collections.defaultdict(float)
                for bins in by_week[wk]:
                    for b, v in bins.items():
                        tot[b] += v
                va = CX.value_area(dict(tot))
                if va[0] is None:
                    va = None
            cache[wk] = va
        if cache[wk] is not None:
            out[ses] = cache[wk]
    return out


def prev_close(r, inst, session):
    """Yesterday's 16:00 close: the last cash trade of the latest earlier
    session that has one, no more than 4 calendar days before."""
    cl = r.cash_close.get(inst, {})
    earlier = sorted(s for s in cl if s < session)
    if not earlier:
        return None
    s = earlier[-1]
    if (_date(session) - _date(s)).days > CLOSE_MAX_DAYS:
        return None
    return cl[s]


def yday_mids(grid):
    """{session: (YDAY_HIGH + YDAY_LOW) / 2} from wave eleven's copy of
    the runner's levels (fixed for the session)."""
    out = {}
    for g in grid:
        ses = g['session']
        if ses in out:
            continue
        lv = g.get('w11_lv') or ()
        if len(lv) > max(_IH, _IL) and lv[_IH] is not None and \
                lv[_IL] is not None:
            out[ses] = (lv[_IH] + lv[_IL]) / 2.0
    return out


def levels_by_instrument(r):
    """{instrument: [level dicts with ses_idx]} for the four groups."""
    out = {}
    for inst, grid in sorted(grid_by_instrument(r).items()):
        span = {}
        for g in grid:
            s = span.setdefault(g['session'], [g['t'], g['t']])
            s[0], s[1] = min(s[0], g['t']), max(s[1], g['t'])
        ses_list = sorted(span)
        onv = on_values(r, inst)
        wkv = week_values(r, inst, ses_list)
        mids = yday_mids(grid)
        lv = []

        def add(kind, group, px, ses, t_on, t_off):
            lv.append(dict(id='%s@%s' % (kind, ses), kind=kind, group=group,
                           price=px, t_on=t_on, t_off=t_off, session=ses))
        for ses in ses_list:
            t0, t1 = span[ses][0], span[ses][1] + 1.0
            if ses in onv:
                poc, vah, val, t930 = onv[ses]
                for kind, px in (('ON_POC', poc), ('ON_VAH', vah),
                                 ('ON_VAL', val)):
                    add(kind, 'ONVA', px, ses, t930, t930 + ON_UNTIL_S)
            if ses in wkv:
                for kind, px in zip(('LW_POC', 'LW_VAH', 'LW_VAL'), wkv[ses]):
                    add(kind, 'WKVA', px, ses, t0, t1)
            c = prev_close(r, inst, ses)
            if c is not None:
                add('YDAY_CLOSE', 'CLOSE', c, ses, t0, t1)
            if ses in mids:
                add('YDAY_MID', 'MID', mids[ses], ses, t0, t1)
        for x in lv:
            x['ses_idx'] = bisect.bisect_left(ses_list, x['session'])
        out[inst] = lv
    return out


# ---------------------------------------------------------------------
# registration 3: wave thirteen's event against another value area
# ---------------------------------------------------------------------
def reentry_events(r, va_at, family):
    """Wave thirteen's back-into-value events (its rule, unchanged) where
    va_at(instrument, session) gives (POC, VAH, VAL, known from) or
    None; grid records before `known from` are not looked at."""
    runs = collections.defaultdict(list)
    for g in r.grid:
        runs[(g['instrument'], g['run'])].append(g)
    out = []
    for (inst, run), grid in sorted(runs.items(),
                                    key=lambda kv: (kv[0][0],
                                                    min(g['t'] for g in kv[1]))):
        grid = sorted(grid, key=lambda g: g['t'])
        gmap = {int(round(g['t'])): g for g in grid}
        state, va_of = {}, {}
        for g in grid:
            mid, ses = g.get('mid'), g['session']
            if ses not in va_of:
                va_of[ses] = va_at(inst, ses)
            va = va_of[ses]
            if mid is None or va is None or g['t'] < va[3]:
                continue
            poc, vah, val = va[0], va[1], va[2]
            b = state.get(ses)
            if b is None:
                if mid >= vah + VA.OUT_TICKS * TICK - 1e-9:
                    state[ses] = 1
                elif mid <= val - VA.OUT_TICKS * TICK + 1e-9:
                    state[ses] = -1
                continue
            back = mid <= vah - TICK + 1e-9 if b > 0 else \
                mid >= val + TICK - 1e-9
            if not back:
                continue
            state[ses] = None
            if not VA.ENTRY_FROM <= RUN.sod_seconds(g['t']) < VA.ENTRY_TO:
                continue
            g0 = gmap.get(int(round(g['t'])) - VA.SPEED_S)
            if g0 is None or g0.get('mid') is None:
                continue
            if b * (g0['mid'] - mid) < VA.SPEED_TICKS * TICK - 1e-9:
                continue
            if not VA.into_value(g, b):
                continue
            out.append(dict(instrument=inst, session=ses, run=run, b=b,
                            direction=-b, t=g['t'], poc=poc, vah=vah,
                            val=val, family=family))
    return out


# ---------------------------------------------------------------------
# registration 4: untested POCs as targets
# ---------------------------------------------------------------------
def naked_pocs(r, inst, grid):
    """[dict(session, price, ses_idx, t_touch)]: each complete cash
    session's POC and the first time, in a later session within its 5,
    a recorded mid was at it or the mids since the following session's
    first record had been on both sides of it (None: not in that time)."""
    ses_list = sorted({g['session'] for g in grid})
    run_ses = {}
    for g in grid:
        run_ses.setdefault(g['run'], g['session'])
    paths = sorted(((ts, ps, run_ses.get(run) or RUN.session_id(ts[0]))
                    for (i, run), (ts, ps) in V.compressed_paths(r).items()
                    if i == inst and len(ts)), key=lambda x: x[0][0])
    pocs = [dict(session=s, price=va[0],
                 ses_idx=bisect.bisect_left(ses_list, s), t_touch=None,
                 lo=None, hi=None)
            for s, va in sorted(r.values.get(inst, {}).items())]
    for ts, ps, ses in paths:
        si = bisect.bisect_left(ses_list, ses)
        act = [p for p in pocs if p['t_touch'] is None and
               p['session'] < ses and si <= p['ses_idx'] + NAKED_SESSIONS]
        if not act:
            continue
        pmin, pmax = min(ps), max(ps)
        for p in act:
            lo = pmin if p['lo'] is None else min(p['lo'], pmin)
            hi = pmax if p['hi'] is None else max(p['hi'], pmax)
            if lo <= p['price'] <= hi:
                a, b = p['lo'], p['hi']
                for tt, x in zip(ts, ps):
                    a = x if a is None or x < a else a
                    b = x if b is None or x > b else b
                    if a <= p['price'] <= b:
                        p['t_touch'] = tt
                        break
            p['lo'], p['hi'] = lo, hi
    for p in pocs:
        del p['lo'], p['hi']
    return pocs


def naked_target(direction, p0, t, session, ses_i, pocs):
    """(target ticks, True) to 2 ticks short of the nearest untested POC
    at least 10 points ahead; (the fixed 100, False) without one."""
    best = None
    for p in pocs:
        if not (p['session'] < session and
                ses_i <= p['ses_idx'] + NAKED_SESSIONS):
            continue
        if p['t_touch'] is not None and p['t_touch'] <= t:
            continue
        dist = direction * (p['price'] - p0) / TICK
        if dist >= NAKED_MIN_AHEAD - 1e-9 and (best is None or dist < best):
            best = dist
    if best is None:
        return LB.TARGET, False
    return best - NAKED_SHORT, True


def score_naked(r, events, pocs_of, ses_lists):
    """[(event, {FIXED|NAKED: (outcome, ticks, target, real)}, None)] for
    the L2 events both versions resolve."""
    paths = V.compressed_paths(r)
    out = []
    for e in events:
        inst = e['instrument']
        key = (inst, e.get('run'))
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        d, p0 = e['direction'], ps[i]
        si = bisect.bisect_left(ses_lists.get(inst, []), e['session'])
        tgt, real = naked_target(d, p0, e['t'], e['session'], si,
                                 pocs_of.get(inst, []))
        res = {}
        for name, tg, rl in (('FIXED', LB.TARGET, True),
                             ('NAKED', tgt, real)):
            o, v, _s = LB.path_exit(ts, ps, i, d, tg, LB.FIXED_STOP)
            res[name] = (o, v, tg, rl)
        if any(x[0] == 'UNRESOLVED' for x in res.values()):
            continue
        out.append((e, res, None))
    return out


# ---------------------------------------------------------------------
# registration 5: the verdicts
# ---------------------------------------------------------------------
def paired_verdict(rows, inst, tid):
    """The POC target against the fixed 25 on the trades that have an
    untested POC ahead."""
    real = [x for x in rows if x[1]['NAKED'][3]]
    x = W.paired_stats(real, inst, 'NAKED')
    x.update(test=tid, name=NAMES[tid], trades=x['n'],
             without_poc=len(rows) - len(real))
    if real:
        by = collections.defaultdict(list)
        for e, res, _m in real:
            by[e['session']].append(
                W.net_points(inst, res['NAKED'][0], res['NAKED'][1]) -
                W.net_points(inst, res['FIXED'][0], res['FIXED'][1]))
        best = max(by, key=lambda s: (sum(by[s]), s))
        rest = [v for s, vs in by.items() if s != best for v in vs]
        x['without_best_day'] = dict(
            session=best, n=len(rest),
            mean_diff_points=round(sum(rest) / len(rest), 3) if rest
            else None)
    if inst != PRIMARY:
        x['status'], x['reasons'] = 'DESCRIBED (not tested)', []
        return x
    if x['n'] < MIN_TRADES:
        x['status'], x['reasons'] = 'NOT ENOUGH TRADES', [
            '%d of the %d trades needed' % (x['n'], MIN_TRADES)]
        return x
    reasons = []
    ci = x.get('ci95_diff_points')
    if x['mean_diff_points'] is None or x['mean_diff_points'] <= 0:
        reasons.append('no better than the fixed 25')
    elif not ci or ci[0] <= 0:
        reasons.append('could be luck: the 95 % range reaches zero')
    wb = x['without_best_day']
    if not wb['n'] or wb['mean_diff_points'] is None or \
            wb['mean_diff_points'] <= 0:
        reasons.append('rests on one day: without %s it is no better'
                       % wb['session'])
    x['status'] = 'NOT PROVEN' if reasons else 'PASS'
    x['reasons'] = reasons
    return x


def apply_holm(rows, label):
    """rows: one family's NQ verdicts. A test with 30+ trades that Holm
    does not reject is NOT PROVEN."""
    ps = [x.get('p') if x['n'] >= MIN_TRADES else None for x in rows]
    for x, rj in zip(rows, BM.holm(ps, HOLM_ALPHA)):
        x['holm_rejected'] = rj
        if x['n'] >= MIN_TRADES and not rj:
            x['status'] = 'NOT PROVEN'
            if not any('luck' in m for m in x['reasons']):
                x['reasons'] = x['reasons'] + [
                    'could be luck after allowing for %s (Holm)' % label]


_KEEP_WITHHELD = ('test', 'name', 'n', 'sessions', 'trades', 'status',
                  'reasons')


def _withhold(row):
    return dict((k, row[k]) for k in _KEEP_WITHHELD if k in row)


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = ProfileLevelsRunner(capture_dir, unblind=unblind, holdout=holdout,
                            max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s): secondary tests' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    grid_of = grid_by_instrument(r)
    ses_lists = {i: sorted({g['session'] for g in gr})
                 for i, gr in grid_of.items()}
    levels = levels_by_instrument(r)
    wick = [e for e in OL.wick_events(r, levels) if keep(e['session'])]
    first_ids = {id(e) for e in OL.first_signals(wick)}
    wick_sc = OL.score(r, wick)
    onv = {i: on_values(r, i) for i in grid_of}
    wkv = {i: week_values(r, i, ses_lists[i]) for i in grid_of}
    never = float('-inf')
    re_sc = {
        'RE-ON': OL.score(r, [e for e in reentry_events(
            r, lambda i, s: onv.get(i, {}).get(s), 'ONVA')
            if keep(e['session'])]),
        'RE-WK': OL.score(r, [e for e in reentry_events(
            r, lambda i, s: wkv[i][s] + (never,)
            if s in wkv.get(i, {}) else None, 'WKVA')
            if keep(e['session'])])}
    l2 = [e for e in V.variant_events(r) if keep(e['session'])]
    l2_first = {id(e) for e in FS.first_signals(l2)}
    pocs = {i: naked_pocs(r, i, gr) for i, gr in grid_of.items()}
    np_sc = score_naked(r, l2, pocs, ses_lists)
    insts = sorted(set(r.instruments) | {PRIMARY})
    results = dict(levels={g: {} for g in GROUPS},
                   reentry={k: {} for k in REENTRY},
                   targets={k: {} for k in TARGETS})
    for inst in insts:
        for g in GROUPS:
            mine = lambda firsts: V.one_at_a_time(   # noqa: E731
                [x for x in wick_sc if x[0]['instrument'] == inst and
                 x[0]['group'] == g and (not firsts or id(x[0]) in first_ids)])
            ver = FS.verdict(mine(True), inst)
            ver.update(test=g, name=NAMES[g])
            b = LB.test_stats(mine(False), inst)
            results['levels'][g][inst] = dict(test=ver, every=dict(
                n=b['n'], sessions=b.get('sessions', 0), hit=b.get('hit'),
                net_points=b.get('net_points')))
        for k in REENTRY:
            ver = FS.verdict(V.one_at_a_time(
                [x for x in re_sc[k] if x[0]['instrument'] == inst]), inst)
            ver.update(test=k, name=NAMES[k])
            results['reentry'][k][inst] = dict(test=ver)
        mine = [x for x in np_sc if x[0]['instrument'] == inst]
        results['targets']['NP-ALL'][inst] = dict(
            test=paired_verdict(mine, inst, 'NP-ALL'))
        results['targets']['NP-FIRST'][inst] = dict(test=paired_verdict(
            [x for x in mine if id(x[0]) in l2_first], inst, 'NP-FIRST'))
    withheld = []
    for fam, ids, label in FAMILIES:
        if PRIMARY in results[fam][ids[0]]:
            apply_holm([results[fam][k][PRIMARY]['test'] for k in ids], label)
        for k in ids:
            rows = results[fam][k]
            if (unblind or holdout) and \
                    rows[PRIMARY]['test']['n'] < MIN_TRADES:
                withheld.append(k)
                for inst in rows:
                    x = _withhold(rows[inst]['test'])
                    x['status'] = (
                        'NOT ENOUGH TRADES: results withheld until a read '
                        'holds %d' % MIN_TRADES if inst == PRIMARY
                        else 'withheld')
                    rows[inst] = dict(test=x)
            elif not (unblind or holdout):
                for inst in rows:
                    rows[inst]['test']['status'] += \
                        ' (DEV: describes, not a test)'
    rep = dict(wave20=W20_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, min_trades=MIN_TRADES,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted(
                   {e['session'] for e in wick} |
                   {x[0]['session'] for v in re_sc.values() for x in v} |
                   {x[0]['session'] for x in np_sc}),
               levels=dict((inst, dict(collections.Counter(
                   x['group'] for x in lv if keep(x['session']))))
                   for inst, lv in levels.items()),
               pocs=dict((inst, len(v)) for inst, v in pocs.items()),
               results=results)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave20'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'levels built: %s' % ('; '.join(
                 '%s %s' % (inst, ', '.join('%s %d' % (g, c.get(g, 0))
                                            for g in GROUPS))
                 for inst, c in sorted(rep['levels'].items())) or '-'),
             'cash-session POCs kept: %s' % (', '.join(
                 '%s %d' % kv for kv in sorted(rep['pocs'].items())) or '-'),
             'target 25 pts, stop 15 pts, 30 min, one trade at a time, net '
             'after costs; NP: the POC target minus the fixed 25 on the '
             'same trades']
    for fam, ids, _label in FAMILIES:
        for k in ids:
            for inst, res in sorted(rep['results'][fam][k].items(),
                                    key=lambda kv: kv[0] != PRIMARY):
                x = res['test']
                lines.append('')
                lines.append('%s  %s%s' % (inst, NAMES[k], ' (tested)'
                                           if inst == PRIMARY else ''))
                lines.append('   trades %d over %d days' % (
                    x['n'], x.get('sessions', 0)))
                if k in rep['withheld']:
                    lines.append('   %s' % x['status'])
                    continue
                if x['n'] and fam == 'targets':
                    ci = x.get('ci95_diff_points')
                    lines.append('   POC target: won %.0f%%, net %s a trade '
                                 '(fixed 25: %s); mean target %.1f pts' % (
                                     100 * x['win'], _pts(x['net_points']),
                                     _pts(x['fixed_net_points']),
                                     x['mean_target_points']))
                    lines.append('   difference %s a trade, 95%% range %s   '
                                 'p %s' % (
                                     _pts(x['mean_diff_points']),
                                     '-' if not ci else '%s .. %s' % (
                                         _pts(ci[0]), _pts(ci[1])),
                                     '-' if x.get('p') is None
                                     else '%.4f' % x['p']))
                    wb = x['without_best_day']
                    lines.append('   without the best day (%s): %d trades, '
                                 'difference %s' % (
                                     wb['session'], wb['n'],
                                     _pts(wb['mean_diff_points'])))
                elif x['n']:
                    ci = x.get('ci95_net_ticks')
                    lines.append('   won %.0f%%, net %s a trade, total %s '
                                 'points' % (100 * x['hit'],
                                             _pts(x['net_points']),
                                             _pts(x.get('total_net_points'))))
                    lines.append('   95%% range of net a trade: %s   p %s' % (
                        '-' if not ci else '%s .. %s points' % (
                            _pts(ci[0] / 4.0), _pts(ci[1] / 4.0)),
                        '-' if x.get('p') is None else '%.4f' % x['p']))
                    wb = x['without_best_day']
                    lines.append('   without the best day (%s): %d trades, '
                                 'net %s a trade' % (
                                     wb['session'], wb['n'],
                                     _pts(wb['net_points'])))
                lines.append('   VERDICT: %s%s' % (x['status'], (
                    ': ' + '; '.join(x['reasons'])) if x.get('reasons')
                    else ''))
                if fam == 'targets':
                    lines.append('   beside: %d L2 trades had no untested '
                                 'POC 10+ points ahead' % x['without_poc'])
                elif 'every' in res:
                    b = res['every']
                    lines.append('   beside, not tested: every signal %d '
                                 'trades, %s, net %s a trade' % (
                                     b['n'], '-' if not b['n'] else
                                     'won %.0f%%' % (100 * b['hit']),
                                     _pts(b['net_points'])))
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
        print('*** %s: this read is wave twenty\'s registered tests. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\nwave-twenty report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W20_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W20_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
