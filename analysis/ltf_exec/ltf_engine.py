#!/usr/bin/env python3
# ======================================================================
# LTF EXECUTION ENGINE - complete, deterministic, genuine-data-only
# ======================================================================
# One command runs the whole study on whatever GENUINE lower-timeframe
# data exists. Nothing is interpolated or synthesized: a timeframe that
# has no real bars reports INSUFFICIENT DATA for every arm that needs it.
#
#   python3 ltf_engine.py inventory
#   python3 ltf_engine.py validate <ltf_dir>
#   python3 ltf_engine.py run <ltf_dir> [--tf 30s,15s,5s]
#
# <ltf_dir> holds V41_LTF_*.csv from MnqV41LtfCaptureHost (Market
# Replay), and/or files produced by ph2_to_ltf.py from the already
# validated genuine 30s history.
#
# Canonical OFH13 parents are regenerated from frozen cand_spec and are
# never redefined. No LTF bar before parentAvailableTime is used. Every
# parent appears in the output for every arm, triggered or not.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, datetime, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import cand_spec as CS
import prospective as P

COST = 0.87
TICK = 0.25
# Isolated aggregation mismatches are quarantined, not tolerated. The cap is
# a RATE so it scales with the sample: an absolute cap would fail a clean
# capture simply for being large. The floor keeps small samples workable.
# The 33-mismatch/17,190-minute duplicate defect this gate caught earlier is
# 0.19% and still fails; a clean capture runs around 0.013%.
QUARANTINE_RATE = 0.0005
QUARANTINE_FLOOR = 10
SEC = {'30s': 30, '15s': 15, '5s': 5}

# arms and the timeframes each needs
ARMS = {
    'ARM0_CANONICAL':            (None, None),
    'ARM1_RECLAIM':              ('exec', None),
    'ARM2_PULLBACK_REEXPAND':    ('exec', None),
    'ARM3_SWEEP_RECLAIM':        ('exec', None),
    'ARM4_DETECT_CONFIRM':       ('fine', 'exec'),
    'ARM5_SECOND_PUSH':          ('exec', None),
    'ARM6_V_RECOVERY':           ('exec', None),
    'ARM7_COMPRESSION_RELEASE':  ('exec', 'fine'),
    'ARM8_FVG_BREAKDOWN':        ('exec', None),
}


# ------------------------------------------------------------------ data
def load_ltf(d, report=False):
    """All genuine LTF bars, grouped by timeframe.

    The capture host APPENDS, so re-running an overlapping date range
    writes that day's bars twice. Duplicates are dropped FIRST-WINS on
    (timeframe, timestamp) - the same rule cand_spec.load_merged uses -
    and any duplicate whose values CONFLICT is reported, because that
    would mean two runs disagreed about the same bar rather than simply
    re-exporting it.
    """
    out, seen, dup, conflict = {}, {}, 0, []
    for f in sorted(glob.glob(os.path.join(d, 'V41_LTF_*.csv'))):
        for r in csv.DictReader(open(f)):
            tf = r['timeframe']
            if tf not in SEC:
                continue
            b = {'et': r['timestampET'],
                 'o': float(r['open']), 'h': float(r['high']),
                 'l': float(r['low']), 'c': float(r['close']),
                 'v': float(r['volume']) if r['volume'] else 0.0,
                 'delta': float(r['delta']) if r.get('delta') else None}
            k = (tf, b['et'])
            if k in seen:
                dup += 1
                p = seen[k]
                if (p['o'], p['h'], p['l'], p['c'], p['v']) != \
                   (b['o'], b['h'], b['l'], b['c'], b['v']):
                    conflict.append(k)
                continue
            seen[k] = b
            out.setdefault(tf, []).append(b)
    for tf in out:
        out[tf].sort(key=lambda x: x['et'])
    if report and dup:
        print('  duplicate rows dropped (first-wins): %d   conflicting: %d'
              % (dup, len(conflict)))
        for k in conflict[:5]:
            print('    CONFLICT %s %s' % k)
    if conflict:
        raise SystemExit('ABORT: %d duplicated bars have CONFLICTING values. '
                         'Two captures disagree about the same bar - resolve '
                         'before any backtest.' % len(conflict))
    return out


def inventory(d=None):
    print('GENUINE LOWER-TIMEFRAME INVENTORY')
    got = load_ltf(d) if d and os.path.isdir(d) else {}
    for tf in ('30s', '15s', '5s'):
        rows = got.get(tf, [])
        if not rows:
            print('  %-4s NOT AVAILABLE' % tf)
            continue
        days = sorted(set(r['et'][:10] for r in rows))
        hasd = sum(1 for r in rows if r['delta'] is not None)
        print('  %-4s AVAILABLE  rows %6d  days %3d  %s .. %s  delta on %d rows'
              % (tf, len(rows), len(days), days[0], days[-1], hasd))
    return got


def validate(d, want_q=False):
    """Exact upward-aggregation gates. No backtest until these pass."""
    quarantine = set()
    got = load_ltf(d, report=True)
    one = {}          # 1m is also first-wins: never let a re-run overwrite
    for f in sorted(glob.glob(os.path.join(d, 'V41_LTF_*.csv'))):
        for r in csv.DictReader(open(f)):
            if r['timeframe'] == '1m' and r['timestampET'] not in one:
                one[r['timestampET']] = {'o': float(r['open']), 'h': float(r['high']),
                                         'l': float(r['low']), 'c': float(r['close'])}
    ok = True
    pairs = [('5s', '15s', 3), ('15s', '30s', 2), ('30s', '1m', 2),
             ('15s', '1m', 4), ('5s', '1m', 12)]
    for src, dst, n in pairs:
        A = got.get(src)
        Bt = got.get(dst) if dst != '1m' else None
        tgt = {b['et']: b for b in Bt} if Bt else one
        if not A or not tgt:
            print('  %-8s -> %-3s  SKIPPED (missing %s)'
                  % (src, dst, src if not A else dst))
            continue
        step = SEC.get(dst, 60)
        gb = {}
        for a in A:
            t = datetime.datetime.strptime(a['et'], '%Y-%m-%d %H:%M:%S')
            secs = t.hour * 3600 + t.minute * 60 + t.second
            anchor = t + datetime.timedelta(seconds=(-secs) % step)
            gb.setdefault(anchor.strftime('%Y-%m-%d %H:%M:%S'), []).append(a)
        m = ex = 0
        bads = []
        for k, g in gb.items():
            if len(g) != n or k not in tgt:
                continue
            g.sort(key=lambda x: x['et'])
            m += 1
            t = tgt[k]
            if (abs(g[0]['o'] - t['o']) < 1e-9
                    and abs(max(x['h'] for x in g) - t['h']) < 1e-9
                    and abs(min(x['l'] for x in g) - t['l']) < 1e-9
                    and abs(g[-1]['c'] - t['c']) < 1e-9):
                ex += 1
            else:
                bads.append(k)
        bad = len(bads)
        # The gate stays EXACT - no tolerance is ever applied to a bar.
        # A handful of isolated mismatches are a tick-boundary artifact:
        # one trade assigned to the far side of a boundary in one series
        # but not the other. Those minutes are QUARANTINED (excluded from
        # the study), never accepted. Anything beyond a handful is
        # systematic - a real data defect - and remains a hard FAIL.
        cap = max(QUARANTINE_FLOOR, int(QUARANTINE_RATE * m))
        tolerable = bad <= cap
        verdict = ('PASS' if not bad else
                   ('PASS (%d quarantined, cap %d)' % (bad, cap) if tolerable
                    else 'FAIL (%d > cap %d)' % (bad, cap))) \
            if m else 'NO OVERLAP'
        print('  %-8s -> %-3s  matched %6d  exact %6d  mismatch %4d   %s'
              % (src, dst, m, ex, bad, verdict))
        if bad:
            for k in sorted(bads)[:20]:
                print('        quarantined minute %s' % k)
            quarantine.update(bads)
            if not tolerable:
                ok = False
    return (ok, quarantine) if want_q else ok


# --------------------------------------------------------------- parents
def parents():
    B = CS.load_merged()
    EV, SIGS, CTX = CS.generate(B)
    assert len(EV['OFH13']) == 133, 'canonical reproduction FAILED - STOP'
    spec = P.REGISTRY['OFH13_PROSPECTIVE_V1']
    bidx = {b['et']: j for j, b in enumerate(B)}
    out = []
    for e in EV['OFH13']:
        o = P.score_one(B, e, spec)
        out.append({'pid': e['id'], 'd': e['d'], 'avail': B[e['j']]['et'],
                    'px': e['entry_px'], 'atr': e['atr'], 'j': e['j'],
                    'zLo': e['meta']['zLo'], 'zHi': e['meta']['zHi'],
                    'day': e['day'], 'stop': o['stop_pt'],
                    'base_net': o['net_pt'], 'base_mfe': o['mfe'],
                    'base_mae': o['mae'], 'base_reason': o['exit_reason'],
                    'part': 'U' if e['day'] <= '2025-11-01'
                            else ('DEV' if e['day'] <= '2026-03-31' else 'IR')})
    return B, bidx, out


# ------------------------------------------------------------------ arms
def swings(bars, left=2, right=2):
    hi, lo = [], []
    for i in range(left, len(bars) - right):
        w = bars[i - left:i + right + 1]
        if all(bars[i]['h'] >= x['h'] for x in w):
            hi.append((i + right, bars[i]['h']))
        if all(bars[i]['l'] <= x['l'] for x in w):
            lo.append((i + right, bars[i]['l']))
    return hi, lo


def window(bars, p, minutes=30):
    """Bars after parent availability while the parent stays valid."""
    t0 = p['avail']
    end = (datetime.datetime.strptime(t0, '%Y-%m-%d %H:%M:%S')
           + datetime.timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    live = []
    for b in bars:
        if b['et'] <= t0 or b['et'] > end:
            continue
        if p['d'] > 0 and b['c'] < p['zLo']:
            break
        if p['d'] < 0 and b['c'] > p['zHi']:
            break
        live.append(b)
    return live


def run_arm(arm, p, ex, fine):
    """Returns (triggered, entry_et, entry_px, reason)."""
    d = p['d']
    if arm == 'ARM0_CANONICAL':
        return True, p['avail'], p['px'], ''
    if not ex:
        return False, None, None, 'NO_LTF_BARS_IN_WINDOW'
    hi, lo = swings(ex)

    if arm == 'ARM1_RECLAIM':
        for k in range(len(ex)):
            lv = [x for i, x in (hi if d > 0 else lo) if i <= k]
            if lv and ((d > 0 and ex[k]['c'] > lv[-1]) or (d < 0 and ex[k]['c'] < lv[-1])):
                return True, ex[k]['et'], ex[k]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM2_PULLBACK_REEXPAND':
        pb = None
        for k in range(len(ex)):
            against = (ex[k]['c'] < ex[k]['o']) if d > 0 else (ex[k]['c'] > ex[k]['o'])
            if pb is None:
                if against:
                    pb = k
                continue
            with_ = (ex[k]['c'] > ex[k]['o']) if d > 0 else (ex[k]['c'] < ex[k]['o'])
            if with_:
                return True, ex[k]['et'], ex[k]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM3_SWEEP_RECLAIM':
        for k in range(len(ex)):
            lv = [x for i, x in (lo if d > 0 else hi) if i <= k]
            if not lv:
                continue
            e0 = lv[-1]
            swept = (ex[k]['l'] < e0) if d > 0 else (ex[k]['h'] > e0)
            if not swept:
                continue
            for m in range(k + 1, min(k + 4, len(ex))):
                back = (ex[m]['c'] > e0) if d > 0 else (ex[m]['c'] < e0)
                if back:
                    return True, ex[m]['et'], ex[m]['c'], ''
            return False, None, None, 'SWEEP_NO_RECLAIM'
        return False, None, None, 'NO_SWEEP'

    if arm == 'ARM4_DETECT_CONFIRM':
        if not fine:
            return False, None, None, 'INSUFFICIENT DATA - finer tf absent'
        fh, fl = swings(fine)
        det = None
        for k in range(len(fine)):
            lv = [x for i, x in (fl if d > 0 else fh) if i <= k]
            if lv and ((d > 0 and fine[k]['l'] < lv[-1]) or (d < 0 and fine[k]['h'] > lv[-1])):
                det = fine[k]['et']
                break
        if det is None:
            return False, None, None, 'NO_DETECTION'
        rng = [b for b in ex if b['et'] >= det]
        if not rng:
            return False, None, None, 'NO_CONFIRM_BARS'
        ref = rng[0]['h'] if d > 0 else rng[0]['l']
        for b in rng[1:]:
            if (d > 0 and b['c'] > ref) or (d < 0 and b['c'] < ref):
                return True, b['et'], b['c'], ''
        return False, None, None, 'NO_CONFIRM'

    if arm == 'ARM5_SECOND_PUSH':
        for k in range(2, len(ex)):
            p1 = min(x['l'] for x in ex[:k]) if d > 0 else max(x['h'] for x in ex[:k])
            near = (ex[k]['l'] <= p1 + 0.05 * p['atr']) if d > 0 else \
                   (ex[k]['h'] >= p1 - 0.05 * p['atr'])
            beyond = (p1 - ex[k]['l']) if d > 0 else (ex[k]['h'] - p1)
            if near and beyond <= 0.25 * p['atr']:
                for m in range(k + 1, min(k + 5, len(ex))):
                    trig = (ex[m]['c'] > ex[k]['h']) if d > 0 else (ex[m]['c'] < ex[k]['l'])
                    if trig:
                        return True, ex[m]['et'], ex[m]['c'], ''
                return False, None, None, 'NO_RECLAIM_AFTER_PUSH2'
        return False, None, None, 'NO_SECOND_PUSH'

    if arm == 'ARM6_V_RECOVERY':
        for k in range(3, len(ex)):
            fl_ = (ex[k - 3]['c'] - ex[k]['l']) if d > 0 else (ex[k]['h'] - ex[k - 3]['c'])
            if fl_ < 0.4 * p['atr']:
                continue
            e0 = ex[k]['l'] if d > 0 else ex[k]['h']
            for m in range(k + 1, min(k + 5, len(ex))):
                rec = (ex[m]['c'] - e0) if d > 0 else (e0 - ex[m]['c'])
                if rec >= 0.5 * fl_:
                    return True, ex[m]['et'], ex[m]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM7_COMPRESSION_RELEASE':
        if not fine:
            return False, None, None, 'INSUFFICIENT DATA - finer tf absent'
        for k in range(4, len(ex)):
            w = ex[k - 4:k]
            comp = (max(x['h'] for x in w) - min(x['l'] for x in w))
            if comp > 0.35 * p['atr']:
                continue
            top = max(x['h'] for x in w)
            bot = min(x['l'] for x in w)
            after = [b for b in fine if b['et'] > w[-1]['et']]
            for b in after[:24]:
                brk = (b['c'] > top) if d > 0 else (b['c'] < bot)
                if brk:
                    return True, b['et'], b['c'], ''
            return False, None, None, 'NO_RELEASE'
        return False, None, None, 'NO_COMPRESSION'

    if arm == 'ARM8_FVG_BREAKDOWN':
        mid = 0.5 * (p['zLo'] + p['zHi'])
        deep = False
        for b in ex:
            through = (b['c'] < p['zLo']) if d > 0 else (b['c'] > p['zHi'])
            if through:
                deep = True
                continue
            if deep:
                back = (b['c'] > mid) if d > 0 else (b['c'] < mid)
                if back:
                    return True, b['et'], b['c'], ''
        return False, None, None, 'NO_BREAKDOWN_RECLAIM' if not deep else 'NO_RECLAIM'
    return False, None, None, 'UNKNOWN_ARM'


# ------------------------------------------------------------- outcomes
def score(B, bidx, p, entry_et, entry_px, slip=0.0, stop_mult=1.5):
    """Manage from the 1m bar containing the LTF entry. Slippage adverse."""
    anchor = entry_et[:17] + '00'
    j = bidx.get(anchor)
    if j is None:
        return None
    px = entry_px + p['d'] * slip
    S = stop_mult * p['atr']
    sp = px - p['d'] * S
    mfe = mae = 0.0
    ff = {}
    thr = [0.10, 0.25, 0.50, 1.00]
    pend = dict((t, None) for t in thr)
    for k in range(1, 61):
        if j + k >= len(B) or B[j + k]['tmin'] - B[j]['tmin'] != k:
            break
        c = B[j + k]
        fav = (c['high'] - px) if p['d'] > 0 else (px - c['low'])
        adv = (px - c['low']) if p['d'] > 0 else (c['high'] - px)
        mfe = max(mfe, fav)
        mae = max(mae, adv)
        for t in thr:
            if pend[t] is None:
                hf, ha = fav >= t * p['atr'], adv >= t * p['atr']
                if hf and ha:
                    pend[t] = 'AMB'
                elif hf:
                    pend[t] = 'FAV'
                elif ha:
                    pend[t] = 'ADV'
        hs = (c['low'] <= sp) if p['d'] > 0 else (c['high'] >= sp)
        if hs:
            return {'net': (sp - px) * p['d'] - COST, 'mfe': mfe, 'mae': mae,
                    'reason': 'STOP', 'held': k, 'ff': pend, 'stop': S}
    end = B[min(j + 60, len(B) - 1)]['close']
    return {'net': (end - px) * p['d'] - COST, 'mfe': mfe, 'mae': mae,
            'reason': 'TIME', 'held': 60, 'ff': pend, 'stop': S}


def run(d, tfs):
    ok, quarantine = validate(d, want_q=True)
    if not ok:
        print('\nCAPTURE INTEGRITY FAILED - no backtesting performed')
        return
    got = load_ltf(d)
    B, bidx, P_ = parents()
    print('\ncanonical parents: %d' % len(P_))
    if quarantine:
        # drop every LTF bar inside a quarantined minute, all timeframes
        dropped = 0
        for tf in list(got):
            keep = [b for b in got[tf] if b['et'][:16] + ':00' not in quarantine]
            dropped += len(got[tf]) - len(keep)
            got[tf] = keep
        print('\nquarantine: %d minute(s) excluded, %d LTF bars dropped'
              % (len(quarantine), dropped))
        # A quarantined minute inside a parent's window means the LTF price
        # path and the 1m path the BASELINE is scored on disagree for that
        # parent. Dropping two bars would leave arm and baseline measured on
        # different data, so the whole parent leaves the study.
        qt = sorted(datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S')
                    for k in quarantine)
        drop_p = []
        for p in P_:
            t0 = datetime.datetime.strptime(p['avail'], '%Y-%m-%d %H:%M:%S')
            t1 = t0 + datetime.timedelta(minutes=60)
            if any(t0 <= q <= t1 for q in qt):
                drop_p.append(p['pid'])
        if drop_p:
            print('quarantine: %d parent(s) excluded - a quarantined minute '
                  'falls inside their window:' % len(drop_p))
            for pid in drop_p:
                print('    %s' % pid)
            P_ = [p for p in P_ if p['pid'] not in drop_p]
    order = [t for t in ('30s', '15s', '5s') if t in tfs and got.get(t)]
    if not order:
        print('no genuine bars for requested timeframes -> INSUFFICIENT DATA')
        return
    rows = []
    for tf in order:
        finer = {'30s': '15s', '15s': '5s'}.get(tf)
        fine_bars = got.get(finer) if finer else None
        for p in P_:
            ex = window([b for b in got[tf] if b['et'][:10] == p['day']], p)
            fb = window([b for b in fine_bars if b['et'][:10] == p['day']], p) \
                if fine_bars else None
            for arm in ARMS:
                trig, et, px, why = run_arm(arm, p, ex, fb)
                r = {'timeframe': tf, 'parentId': p['pid'], 'direction': p['d'],
                     'day': p['day'], 'partition': p['part'], 'arm': arm,
                     'parentAvailableTime': p['avail'],
                     'canonicalEntryPrice': p['px'],
                     'triggered': 'TRUE' if trig else 'FALSE',
                     'ltfEntryTime': et or '', 'ltfEntryPrice': px if px else '',
                     'noFillReason': why, 'baselineNet': p['base_net']}
                if trig:
                    t0 = datetime.datetime.strptime(p['avail'], '%Y-%m-%d %H:%M:%S')
                    t1 = datetime.datetime.strptime(et, '%Y-%m-%d %H:%M:%S')
                    r['delaySeconds'] = int((t1 - t0).total_seconds())
                    r['entryImprovement'] = (p['px'] - px) * p['d']
                    o = score(B, bidx, p, et, px)
                    if o:
                        r.update({'net': o['net'], 'mfe': o['mfe'], 'mae': o['mae'],
                                  'exitReason': o['reason'], 'stopPts': o['stop']})
                        for t, v in o['ff'].items():
                            r['ff_%.2f' % t] = v or 'NEITHER'
                else:
                    r['delaySeconds'] = ''
                    r['entryImprovement'] = ''
                    r['net'] = ''          # per-parent: no trade taken
                rows.append(r)
    fn = os.path.join(HERE, 'per_parent.csv')
    keys = sorted(set(k for r in rows for k in r))
    with open(fn, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    summarize(rows, P_)
    print('\nwrote %s (%d rows)' % (fn, len(rows)))


def summarize(rows, P_):
    base = {p['pid']: p for p in P_}
    n_par = len(P_)
    top10_all = set(x['pid'] for x in sorted(P_, key=lambda p: -p['base_net'])[:10])
    print('\n%-26s %-5s %5s %6s %7s %8s %8s %7s %7s %6s' %
          ('arm', 'tf', 'trig', 'trig%', 'perParEV', 'vsBase', 'avgImp',
           'medMAE', 'ff0.25', 'top10'))
    out = []
    for tf in sorted(set(r['timeframe'] for r in rows)):
        # Per-parent EV is only meaningful over parents the capture
        # actually covers. A parent with NO LTF bars in its window is a
        # DATA GAP, not an arm declining to trade, and scoring it as a
        # zero would rig every comparison against the arms. Baseline and
        # arms are therefore both restricted to the covered parents, and
        # the coverage is stated outright.
        # ARM0 is the 1m baseline and needs no LTF bar, so it must not
        # vote on coverage - only the LTF arms can tell us whether bars
        # actually existed in a parent's window.
        cov = set(r['parentId'] for r in rows
                  if r['timeframe'] == tf and r['arm'] != 'ARM0_CANONICAL'
                  and r.get('noFillReason') != 'NO_LTF_BARS_IN_WINDOW')
        P_c = [p for p in P_ if p['pid'] in cov] or P_
        n_c = len(P_c)
        base_ev = sum(p['base_net'] for p in P_c) / n_c
        top10 = set(x['pid'] for x in sorted(P_c, key=lambda p: -p['base_net'])[:10])
        print('  BASELINE %-4s (covered)  %-4s  %3d  100.0%%  %+7.2f   %+6.2f    %+5.2f  %6.1f  %5s  %2d/10'
              % (tf, tf, n_c, base_ev, 0.0, 0.0,
                 statistics.median([p['base_mae'] for p in P_c]), '-',
                 len(top10 & top10_all)))
        for arm in ARMS:
            if arm == 'ARM0_CANONICAL':
                continue
            sub = [r for r in rows if r['timeframe'] == tf and r['arm'] == arm
                   and r['parentId'] in cov]
            if not sub:
                continue
            t = [r for r in sub if r['triggered'] == 'TRUE' and r.get('net') != '']
            ev = sum(r['net'] for r in t) / len(sub) if sub else 0.0
            imp = statistics.mean([r['entryImprovement'] for r in t]) if t else float('nan')
            mae = statistics.median([r['mae'] for r in t]) if t else float('nan')
            fav = sum(1 for r in t if r.get('ff_0.25') == 'FAV')
            adv = sum(1 for r in t if r.get('ff_0.25') == 'ADV')
            kept = sum(1 for r in t if r['parentId'] in top10)
            top10n = len(top10)
            print('  %-24s %-5s %4d %6.1f%% %+8.2f %+8.2f %+7.2f %7.1f %6.1f%% %3d/%d'
                  % (arm, tf, len(t), 100.0 * len(t) / len(sub), ev, ev - base_ev,
                     imp, mae, 100.0 * fav / max(1, fav + adv), kept, top10n))
            out.append((arm, tf, ev - base_ev, len(t), kept, n_c, base_ev))
    fn = os.path.join(HERE, 'timeframe_comparison.csv')
    with open(fn, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['arm', 'timeframe', 'perParentEV_minus_baseline',
                    'triggered', 'topWinnersKept', 'coveredParents',
                    'baselinePerParentEV'])
        for a, t, dv, n, k, nc, bev in out:
            w.writerow([a, t, round(dv, 4), n, k, nc, round(bev, 4)])
    print('\nPER-PARENT EV is the primary metric, over the parents the capture')
    print('COVERS. Untriggered-but-covered parents count as 0, so an arm that')
    print('only fires on easy trades cannot hide behind a high win rate; parents')
    print('with no LTF bars at all are excluded from both arm and baseline.')
    if n_c < n_par:
        print('\n*** COVERAGE %d of %d canonical parents. Everything above is a'
              % (n_c, n_par))
        print('*** PIPELINE DEMONSTRATION, NOT A FINDING. Do not read the arm')
        print('*** ordering as evidence at this sample size.')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
    d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'data')
    if cmd == 'inventory':
        inventory(d)
    elif cmd == 'validate':
        validate(d)
    elif cmd == 'run':
        tfs = ['30s', '15s', '5s']
        for a in sys.argv[3:]:
            if a.startswith('--tf'):
                tfs = a.split('=')[-1].split(',') if '=' in a else tfs
        run(d, tfs)
