#!/usr/bin/env python3
"""mrofyt_smt.py - MROF-YT-W6B-SMT-1.0

MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md, part B, turned into running
code: does ES confirm or deny an NQ break of yesterday's high or low,
and does that tell you whether to fade the break or follow it?
(Discretionary traders call the non-confirmation "SMT divergence".)

It needs one-minute bars of NQ and ES only, so it runs on the same
twenty years and the same split as the context study: searched on
nothing (four fixed tests), read on 2019-06-01 .. 2026-06-30 first, and
judged on every session before 2019-06-01, which no study in this
repository has read.

    break     the first cash-session bar (starting 09:30-14:59 ET) that
              trades 0.02 ATR beyond yesterday's high (low), same contract
    FAILED    a bar of the next 15 (the break bar included) closes back
              inside: the event is that close; trade AGAINST the break
    HELD      15 closes in a row beyond the level: the event is the 15th
              close; trade WITH the break
    ES        confirmed when ES has traded 0.02 of ITS ATR beyond ITS
              yesterday's level at any bar up to the event bar
    outcome   stop = max(0.05 ATR, 4 points), target 1.6 x stop, first
              touch on the following minute bars (a bar touching both is
              a stop), else the 15:59 close; in R (stop units), net of
              0.75 points a round trip

    S1  FAILED, ES not confirming, fade:   mean net R > 0
    S2  HELD, ES confirming, follow:       mean net R > 0
    S3  among FAILED: not confirming minus confirming > 0
    S4  among HELD: confirming minus not confirming > 0
    month-clustered t, Holm over the four

    python3 mrofyt_smt.py "<folder with NQ and ES minute exports>" \\
            --out smt_dev.json                  # 2019-06 .. 2026-06
    python3 mrofyt_smt.py "<folder>" --unblind --out smt_val.json
                                                # before 2019-06, once

Exports as for mrofyt_context.py: "NQ 12-26.Last.txt", "ES 12-26.Last.txt"
(UTC, end of bar); --stamps-tz / --stamps as there.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import array
import collections
import datetime as _dt
import json
import math
import os
import re
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_discover as DI

SMT_VERSION = 'MROF-YT-W6B-SMT-1.0'
REGISTRATION = 'MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md'
EXPOSURE_FILE = 'MROF_SMT_EXPOSURE.json'

# registration B1-B3
WINDOW = (9 * 3600 + 1800, 15 * 3600)   # break bar must start in here
BREAK_ATR = 0.02
FAIL_BARS = 15
HOLD_BARS = 15
STOP_ATR = 0.05
STOP_MIN_POINTS = 4.0
TARGET_R = 1.6
COST_POINTS = 0.75
TESTS = ('S1', 'S2', 'S3', 'S4')
MIN_EVENTS = 60
MIN_GROUP = 30
HOLM_ALPHA = 0.05


# ---------------------------------------------------------------------
# reading: the context reader, keeping the cash-session minute bars
# ---------------------------------------------------------------------
class BarDayAgg(CX.DayAgg):
    __slots__ = ('bars',)

    def __init__(self):
        CX.DayAgg.__init__(self)
        self.bars = array.array('d')           # sod, high, low, close

    def add(self, sod, o, h, lo, c, v):
        CX.DayAgg.add(self, sod, o, h, lo, c, v)
        if CX.RTH_OPEN <= sod < CX.RTH_CLOSE:
            self.bars.extend((sod, h, lo, c))

    def finalize(self):
        out = CX.DayAgg.finalize(self)
        out['bars'] = self.bars
        return out


class BarReader(CX.Reader):
    """mrofyt_context's Reader, aggregating with BarDayAgg."""

    def read_file(self, path):
        contract = CX.contract_of(path, self.root) or '%s CONT' % self.root
        aggs = {}
        n = 0
        with open(path, 'r', errors='replace') as fh:
            for line in fh:
                parts = re.split(r'[;,]', line.strip())
                if len(parts) != 6:
                    if line.strip():
                        self.bad_lines += 1
                    continue
                stamp = parts[0].split()
                if len(stamp) < 2 or len(stamp[0]) != 8 or \
                        len(stamp[1]) != 6 or not stamp[0].isdigit():
                    self.bad_lines += 1
                    continue
                try:
                    o, h, lo, c, v = (float(x) for x in parts[1:])
                except ValueError:
                    self.bad_lines += 1
                    continue
                ses, sod = CX.bar_session(stamp[0], stamp[1], self.stamps_tz,
                                          self.stamps)
                if ses >= CX.REFUSE_FROM:
                    self.refused_sessions.add(ses)
                    continue
                if self.allow is not None and not self.allow(ses):
                    self.skipped_sessions.add(ses)
                    continue
                a = aggs.get(ses)
                if a is None:
                    a = aggs[ses] = BarDayAgg()
                a.add(sod, o, h, lo, c, v)
                m = int(sod // 60)
                self.minute_vol[m] += v
                self.minute_n[m] += 1
                n += 1
        for ses, a in aggs.items():
            self.days[(contract, ses)] = a.finalize()
        self.files.append(dict(file=os.path.basename(path), contract=contract,
                               bars=n, sessions=len(aggs)))


def sessions_of(path, root, allow, stamps_tz='UTC', stamps='end'):
    """{session: dict(bars, high_y, low_y, atr)} for the eligible
    sessions of one root: the front contract, its cash-session bars,
    yesterday's cash high and low FROM THE SAME CONTRACT, and ATR."""
    rd = BarReader(root, stamps_tz, stamps, allow)
    rd.read_path(path)
    if not rd.days:
        raise CX.ContextDataError(
            'these exports hold no %s session in the years this mode '
            'reads: export %s minute data for them' % (root, root))
    chk = rd.check_stamps()
    recs = CX.build_days(rd.days)
    # "yesterday" is the session right before, complete, same contract
    # (the context study's rule); an early close yesterday means no level
    every = sorted({s for _c, s in rd.days})
    before = dict(zip(every[1:], every[:-1]))
    out = {}
    for r in recs:
        s = r['session']
        prev = before.get(s)
        if not r['eligible'] or prev is None:
            continue
        y = rd.days.get((r['contract'], prev))
        if y is not None and y['complete']:
            out[s] = dict(bars=rd.days[(r['contract'], s)]['bars'],
                          high_y=y['rth_high'], low_y=y['rth_low'],
                          atr=r['atr'], contract=r['contract'])
    return out, rd, chk


# ---------------------------------------------------------------------
# events and outcomes (pure)
# ---------------------------------------------------------------------
def _rows(bars):
    return [(bars[k], bars[k + 1], bars[k + 2], bars[k + 3])
            for k in range(0, len(bars), 4)]


def find_events(day, es_day):
    """The first break of yesterday's high and of its low, as FAILED or
    HELD events with ES's confirmation. day / es_day: sessions_of()
    entries (es_day None: no event, ES must be there to say)."""
    if es_day is None:
        return []
    rows = _rows(day['bars'])
    es = _rows(es_day['bars'])
    out = []
    for side, level, es_level in ((1, day['high_y'], es_day['high_y']),
                                  (-1, day['low_y'], es_day['low_y'])):
        thr = level + side * BREAK_ATR * day['atr']
        k = None
        for j, (sod, h, lo, _c) in enumerate(rows):
            if not WINDOW[0] <= sod < WINDOW[1]:
                continue
            if (side > 0 and h >= thr) or (side < 0 and lo <= thr):
                k = j
                break
        if k is None:
            continue
        kind = ev = None
        for j in range(k, min(k + FAIL_BARS, len(rows))):
            if side * (rows[j][3] - level) < 0:
                kind, ev = 'FAILED', j
                break
        if kind is None and k + HOLD_BARS - 1 < len(rows) and all(
                side * (rows[j][3] - level) > 0
                for j in range(k, k + HOLD_BARS)):
            kind, ev = 'HELD', k + HOLD_BARS - 1
        if kind is None:
            continue
        es_thr = es_level + side * BREAK_ATR * es_day['atr']
        ev_sod = rows[ev][0]
        confirmed = any(sod <= ev_sod and
                        ((side > 0 and h >= es_thr) or
                         (side < 0 and lo <= es_thr))
                        for sod, h, lo, _c in es)
        out.append(dict(side=side, kind=kind, es_confirmed=confirmed,
                        direction=(-side if kind == 'FAILED' else side),
                        bar=ev, sod=ev_sod, entry=rows[ev][3]))
    return out


def outcome(rows, ev, direction, entry, atr):
    """Path on the bars after `ev`: (label, R gross, R net)."""
    stop = max(STOP_ATR * atr, STOP_MIN_POINTS)
    target = TARGET_R * stop
    for sod, h, lo, c in rows[ev + 1:]:
        if direction > 0:
            hit_s, hit_t = lo <= entry - stop, h >= entry + target
        else:
            hit_s, hit_t = h >= entry + stop, lo <= entry - target
        if hit_s:
            return 'STOP', -1.0, -1.0 - COST_POINTS / stop
        if hit_t:
            return 'TARGET', TARGET_R, TARGET_R - COST_POINTS / stop
    if len(rows) <= ev + 1:
        return 'NONE', None, None
    x = direction * (rows[-1][3] - entry) / stop
    return 'CLOSE', x, x - COST_POINTS / stop


def build_events(nq, es):
    out = []
    for s in sorted(nq):
        day = nq[s]
        rows = _rows(day['bars'])
        for e in find_events(day, es.get(s)):
            lab, rg, rn = outcome(rows, e['bar'], e['direction'], e['entry'],
                                  day['atr'])
            if rg is None:
                continue
            e.update(session=s, month=s[:6], year=s[:4], outcome=lab,
                     r_gross=rg, r_net=rn)
            out.append(e)
    return out


# ---------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------
def mean_stats(vals):
    """vals: [(month, x)]. Month-clustered mean above zero."""
    st = DI.cluster_stats([(m, x, 0.0, x) for m, x in vals])
    return dict(n=st['n'], months=st.get('sessions', 0),
                mean_r=st.get('hit'), t=st.get('t'), p=st.get('p'),
                ci95=st.get('ci95'))


def diff_stats(a, b):
    """a, b: [(month, x)]. mean(a) - mean(b), cluster-robust by month
    over both groups at once (influence-function variance), Student t on
    G - 1 degrees of freedom."""
    na, nb = len(a), len(b)
    if not na or not nb:
        return dict(n_a=na, n_b=nb)
    ma = sum(x for _m, x in a) / na
    mb = sum(x for _m, x in b) / nb
    infl = collections.defaultdict(float)
    for m, x in a:
        infl[m] += (x - ma) / na
    for m, x in b:
        infl[m] -= (x - mb) / nb
    G = len(infl)
    out = dict(n_a=na, n_b=nb, months=G, mean_a=round(ma, 4),
               mean_b=round(mb, 4), diff=round(ma - mb, 4))
    if G >= 2:
        var = G / (G - 1.0) * sum(v * v for v in infl.values())
        se = math.sqrt(var)
        if se > 1e-12:
            t = (ma - mb) / se
            tc = DI.t_crit(G - 1)
            out.update(se=round(se, 5), t=round(t, 3),
                       p=DI.t_p_two_sided(t, G - 1),
                       ci95=(round(ma - mb - tc * se, 4),
                             round(ma - mb + tc * se, 4)))
    return out


def tests(events):
    def grp(kind, conf):
        return [(e['month'], e['r_net']) for e in events
                if e['kind'] == kind and e['es_confirmed'] == conf]
    A, B = grp('FAILED', False), grp('FAILED', True)
    C, D = grp('HELD', True), grp('HELD', False)
    out = [dict(test='S1', what='FAILED, ES not confirming, fade',
                **mean_stats(A)),
           dict(test='S2', what='HELD, ES confirming, follow',
                **mean_stats(C)),
           dict(test='S3', what='FAILED: ES not confirming minus confirming',
                **diff_stats(A, B)),
           dict(test='S4', what='HELD: ES confirming minus not confirming',
                **diff_stats(C, D))]
    rej = BM.holm([x.get('p') for x in out], HOLM_ALPHA)
    for x, rj in zip(out, rej):
        if 'n' in x:
            enough = x['n'] >= MIN_EVENTS
            eff = x.get('mean_r')
        else:
            enough = x['n_a'] >= MIN_GROUP and x['n_b'] >= MIN_GROUP
            eff = x.get('diff')
        if not enough:
            x['status'] = 'NOT TESTED'
        elif rj and eff is not None and eff > 0 and x.get('ci95') and \
                x['ci95'][0] > 0:
            x['status'] = 'PROMISING'
        else:
            x['status'] = 'NO SIGNAL'
    return out


def describe(events):
    by = collections.defaultdict(list)
    for e in events:
        by[(e['kind'], e['es_confirmed'])].append(e['r_net'])
    groups = {'%s %s' % (k[0], 'ES-confirmed' if k[1] else 'ES-not'):
              dict(n=len(v), mean_r_net=round(sum(v) / len(v), 4))
              for k, v in sorted(by.items())}
    years = collections.defaultdict(collections.Counter)
    for e in events:
        years[e['year']][e['kind']] += 1
    return dict(groups=groups,
                events_by_year={y: dict(c) for y, c in sorted(years.items())})


# ---------------------------------------------------------------------
# the modes
# ---------------------------------------------------------------------
def run(path, unblind=False, stamps_tz='UTC', stamps='end'):
    allow = CX.is_validation if unblind else CX.is_dev
    nq, rdn, chk_n = sessions_of(path, 'NQ', allow, stamps_tz, stamps)
    es, rde, chk_e = sessions_of(path, 'ES', allow, stamps_tz, stamps)
    ev = build_events(nq, es)
    rep = dict(smt=SMT_VERSION, registration=REGISTRATION,
               mode='validation' if unblind else 'dev',
               years=('before %s' % CX.VALIDATION_BEFORE) if unblind else
               ('%s to %s' % (CX.VALIDATION_BEFORE, CX.REFUSE_FROM)),
               note=None if unblind else
               'these years were read by earlier studies in this repository '
               '(for other questions); the verdict is the --unblind read',
               stamp_check=dict(NQ=chk_n, ES=chk_e),
               sessions=dict(NQ=len(nq), ES=len(es),
                             both=len(set(nq) & set(es))),
               first_session=min(nq) if nq else None,
               last_session=max(nq) if nq else None,
               sessions_skipped_unread=dict(NQ=len(rdn.skipped_sessions),
                                            ES=len(rde.skipped_sessions)),
               events=len(ev), tests=tests(ev), describe=describe(ev),
               rules=dict(break_atr=BREAK_ATR, fail_bars=FAIL_BARS,
                          hold_bars=HOLD_BARS, stop_atr=STOP_ATR,
                          stop_min_points=STOP_MIN_POINTS,
                          target_r=TARGET_R, cost_points=COST_POINTS))
    return rep, ev


def record_read(rep, path):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=SMT_VERSION, first=rep['first_session'],
        last=rep['last_session'], events=rep['events'],
        at=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def text(rep):
    lines = ['%s  %s  (%s)' % (rep['smt'], rep['mode'], rep['years']),
             'sessions: NQ %d, ES %d, both %d (%s .. %s); stamp check NQ %s, '
             'ES %s' % (rep['sessions']['NQ'], rep['sessions']['ES'],
                        rep['sessions']['both'], rep['first_session'],
                        rep['last_session'],
                        rep['stamp_check']['NQ']['open_minute'],
                        rep['stamp_check']['ES']['open_minute'])]
    if rep.get('note'):
        lines.append('NOTE: ' + rep['note'])
    lines.append('%d break events; R = stop units, net of %.2f points' % (
        rep['events'], COST_POINTS))
    for g, v in rep['describe']['groups'].items():
        lines.append('  %-26s n=%-5d mean net R %+.3f' % (g, v['n'],
                                                          v['mean_r_net']))
    lines.append('')
    for x in rep['tests']:
        if 'n' in x:
            body = 'n=%s months=%s mean R=%s' % (x['n'], x['months'],
                                                 x.get('mean_r'))
        else:
            body = 'n=%s/%s diff=%s' % (x['n_a'], x['n_b'], x.get('diff'))
        lines.append('  %s %-44s %s t=%s p=%s -> %s' % (
            x['test'], x['what'], body, x.get('t'),
            None if x.get('p') is None else round(x['p'], 4), x['status']))
    lines.append('')
    lines.append('Minute bars, first touch, costs charged; not P&L. No order '
                 'was placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    unblind = '--unblind' in argv
    try:
        if unblind:
            print('*** UNBLIND: the four ES tests on the sessions before %s, '
                  'once. ***\n' % CX.VALIDATION_BEFORE)
        rep, _ev = run(argv[0], unblind, stz, stp)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    out = arg('--out')
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nES-confirmation report -> %s' % out)
    if unblind:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         EXPOSURE_FILE)
        print('validation read recorded -> %s (%d read(s))'
              % (p, record_read(rep, p)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
