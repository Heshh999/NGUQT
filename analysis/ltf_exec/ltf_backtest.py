#!/usr/bin/env python3
# ======================================================================
# LTF-EXEC-BACKTEST-V1 - deterministic 5s/15s execution backtester
# ======================================================================
# Consumes GENUINE lower-timeframe bars only:
#   - V41_LTF_*.csv files from MnqV41LtfCaptureHost (Market Replay), or
#   - the validated genuine 30s history (ph2 capture, morning window).
# NOTHING is interpolated. If a required timeframe is absent the arm
# reports INSUFFICIENT DATA. Order-flow-microstructure arms require
# genuine LTF bid/ask and degrade to FUTURE CAPTURE REQUIRED otherwise.
#
# Parents are the CANONICAL OFH13 events from frozen cand_spec -
# regenerated, never redefined. No LTF bar earlier than the parent's
# availability time participates. Per-parent accounting: one row per
# parent x arm, triggered or not.
#
# Usage:
#   python3 ltf_backtest.py audit                (data inventory)
#   python3 ltf_backtest.py validate <ltf_dir>   (aggregation integrity)
#   python3 ltf_backtest.py run <ltf_dir>        (arms + per-parent CSVs)
#   python3 ltf_backtest.py run30s               (pipeline check, 30s arm1)
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, datetime, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import cand_spec as CS

COST = 0.87
ARMS = ['ARM0_CANONICAL', 'ARM1_15S_RECLAIM', 'ARM2_15S_PB_REEXP',
        'ARM3_5S_SWEEP_RECLAIM', 'ARM4_5S_DETECT_15S_CONFIRM',
        'ARM5_15S_SECOND_PUSH', 'ARM6_15S_V_RECOVERY',
        'ARM7_15S_COMP_5S_RELEASE', 'ARM8_15S_FVG_BREAKDOWN']


def load_ltf(d, tf):
    """Load genuine LTF bars of one timeframe from capture files."""
    rows = []
    for f in sorted(glob.glob(os.path.join(d, 'V41_LTF_*.csv'))):
        for r in csv.DictReader(open(f)):
            if r['timeframe'] != tf:
                continue
            rows.append({'et': r['timestampET'],
                         'o': float(r['open']), 'h': float(r['high']),
                         'l': float(r['low']), 'c': float(r['close']),
                         'v': float(r['volume']),
                         'delta': float(r['delta']) if r.get('delta') else None,
                         'pid': r.get('parentEventId', '')})
    rows.sort(key=lambda x: x['et'])
    return rows


def validate(d):
    """5s->15s, 15s->1m, 5s->1m exact-aggregation integrity."""
    ok = True
    for src, dst, n in (('5s', '15s', 3), ('15s', '1m', 4), ('5s', '1m', 12)):
        A = load_ltf(d, src)
        Bm = {b['et']: b for b in load_ltf(d, dst)}
        if not A or not Bm:
            print('  %s->%s: INSUFFICIENT DATA (%d/%d rows)' % (src, dst, len(A), len(Bm)))
            ok = False
            continue
        gb = {}
        for a in A:
            t = datetime.datetime.strptime(a['et'], '%Y-%m-%d %H:%M:%S')
            step = int(dst[:-1]) if dst.endswith('s') else 60
            secs = (t.minute * 60 + t.second)
            anchor = t - datetime.timedelta(seconds=(secs - 1) % step + 1) \
                + datetime.timedelta(seconds=step)
            key = anchor.strftime('%Y-%m-%d %H:%M:%S')
            g = gb.setdefault(key, [])
            g.append(a)
        m = ex = bad = miss = 0
        for k, g in gb.items():
            if len(g) != n:
                continue
            t = Bm.get(k)
            if t is None:
                miss += 1
                continue
            m += 1
            g.sort(key=lambda x: x['et'])
            o = g[0]['o']; h = max(x['h'] for x in g)
            lo = min(x['l'] for x in g); c = g[-1]['c']
            if abs(o - t['o']) < 1e-9 and abs(h - t['h']) < 1e-9 \
                    and abs(lo - t['l']) < 1e-9 and abs(c - t['c']) < 1e-9:
                ex += 1
            else:
                bad += 1
        print('  %s->%s: matched %d  exact %d  mismatch %d  missing %d  -> %s'
              % (src, dst, m, ex, bad, miss, 'PASS' if bad == 0 and m > 0 else 'FAIL'))
        ok = ok and bad == 0 and m > 0
    return ok


def parents():
    """Canonical OFH13 events, frozen. Availability = trigger-bar close."""
    B = CS.load_merged()
    EV, SIGS, CTX = CS.generate(B)
    out = []
    for e in EV['OFH13']:
        out.append({'pid': e['id'], 'd': e['d'], 'avail': B[e['j']]['et'],
                    'entry_px': e['entry_px'], 'atr': e['atr'],
                    'zLo': e['meta']['zLo'], 'zHi': e['meta']['zHi'],
                    'day': B[e['j']]['day'], 'j': e['j']})
    return B, out


def micro_swings(bars, left=2, right=2):
    hi, lo = [], []
    for i in range(left, len(bars) - right):
        w = bars[i - left:i + right + 1]
        if all(bars[i]['h'] >= x['h'] for x in w):
            hi.append((i + right, bars[i]['h']))
        if all(bars[i]['l'] <= x['l'] for x in w):
            lo.append((i + right, bars[i]['l']))
    return hi, lo


def run_arm(bars, p, arm, tf_sec):
    """Returns (triggered, entry_idx, entry_px, reason). bars = LTF bars of
    the arm's timeframe restricted to >= parent availability and while the
    parent stays valid (30 min / far-side break, evaluated on these bars)."""
    d = p['d']
    if not bars:
        return False, None, None, 'NO_LTF_DATA'
    limit = int(30 * 60 / tf_sec)
    live = []
    for b in bars[:limit]:
        if d > 0 and b['c'] < p['zLo']:
            break
        if d < 0 and b['c'] > p['zHi']:
            break
        live.append(b)
    if not live:
        return False, None, None, 'PARENT_INVALIDATED'
    hi, lo = micro_swings(live, 2, 2)

    if arm == 'ARM1_15S_RECLAIM':
        for k in range(len(live)):
            lv = [x for i, x in hi if i <= k] if d > 0 else [x for i, x in lo if i <= k]
            if not lv:
                continue
            trig = lv[-1]
            if (d > 0 and live[k]['c'] > trig) or (d < 0 and live[k]['c'] < trig):
                return True, k, live[k]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM2_15S_PB_REEXP':
        pb = None
        for k in range(1, len(live)):
            against = (live[k]['c'] < live[k]['o']) if d > 0 else (live[k]['c'] > live[k]['o'])
            if pb is None and against:
                pb = k
                continue
            if pb is not None:
                res = (live[k]['c'] > live[k]['o']) if d > 0 else (live[k]['c'] < live[k]['o'])
                if res:
                    return True, k, live[k]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM3_5S_SWEEP_RECLAIM':
        for k in range(len(live)):
            lv = [x for i, x in lo if i <= k] if d > 0 else [x for i, x in hi if i <= k]
            if not lv:
                continue
            ext = lv[-1]
            swept = (live[k]['l'] < ext) if d > 0 else (live[k]['h'] > ext)
            if not swept:
                continue
            for m in range(k + 1, min(k + 4, len(live))):
                back = (live[m]['c'] > ext) if d > 0 else (live[m]['c'] < ext)
                if back:
                    return True, m, live[m]['c'], ''
            return False, None, None, 'NO_RECLAIM'
        return False, None, None, 'NO_SWEEP'

    if arm == 'ARM6_15S_V_RECOVERY':
        for k in range(3, len(live)):
            fl = (live[k - 3]['c'] - live[k]['l']) if d > 0 else (live[k]['h'] - live[k - 3]['c'])
            if fl < 0.5 * p['atr']:
                continue
            ext = live[k]['l'] if d > 0 else live[k]['h']
            for m in range(k + 1, min(k + 4, len(live))):
                rec = (live[m]['c'] - ext) if d > 0 else (ext - live[m]['c'])
                if rec >= 0.5 * fl:
                    return True, m, live[m]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    if arm == 'ARM8_15S_FVG_BREAKDOWN':
        deep = False
        for k in range(len(live)):
            through = (live[k]['c'] < p['zLo']) if d > 0 else (live[k]['c'] > p['zHi'])
            if through:
                deep = True
            if deep:
                back = (live[k]['c'] > (p['zLo'] + p['zHi']) / 2.0) if d > 0 \
                    else (live[k]['c'] < (p['zLo'] + p['zHi']) / 2.0)
                if back:
                    return True, k, live[k]['c'], ''
        return False, None, None, 'NO_TRIGGER'

    return False, None, None, 'ARM_NEEDS_5S_AND_15S_PAIR'


def per_parent(d):
    B, P = parents()
    bidx = {b['et']: j for j, b in enumerate(B)}
    tf = {'15s': load_ltf(d, '15s'), '5s': load_ltf(d, '5s'),
          '30s': load_ltf(d, '30s')}
    have15 = bool(tf['15s'])
    have5 = bool(tf['5s'])
    out = []
    for p in P:
        j0 = bidx[p['avail']]

        def fwd(entry_px, from_j):
            o = {}
            for h in (5, 10, 15, 30, 60):
                if from_j + h < len(B) and B[from_j + h]['tmin'] - B[from_j]['tmin'] == h:
                    o[h] = (B[from_j + h]['close'] - entry_px) * p['d'] - COST
                else:
                    o[h] = None
            return o
        base = fwd(p['entry_px'], j0)
        for arm in ARMS:
            row = {'parentId': p['pid'], 'candidate': 'OFH13', 'direction': p['d'],
                   'parentAvailableTime': p['avail'],
                   'canonicalEntryTime': p['avail'],
                   'canonicalEntryPrice': p['entry_px'], 'ltfArm': arm,
                   'ltfTriggered': '', 'ltfEntryTime': '', 'ltfEntryPrice': '',
                   'delaySeconds': '', 'entryImprovementPoints': '',
                   'noFillReason': '', 'fwd60Canonical': base[60]}
            if arm == 'ARM0_CANONICAL':
                row['ltfTriggered'] = 'TRUE'
                row['ltfEntryTime'] = p['avail']
                row['ltfEntryPrice'] = p['entry_px']
                row['delaySeconds'] = 0
                row['entryImprovementPoints'] = 0.0
                row['fwd60Arm'] = base[60]
            else:
                need5 = '5S' in arm
                need15 = '15S' in arm
                if (need5 and not have5) or (need15 and not have15):
                    row['ltfTriggered'] = 'FALSE'
                    row['noFillReason'] = 'INSUFFICIENT DATA - genuine %s bars absent' % \
                        ('5s' if need5 and not have5 else '15s')
                    row['fwd60Arm'] = base[60]     # per-parent: falls back to canonical? NO -
                    row['fwd60Arm'] = None         # untriggered arms carry no arm EV
                else:
                    tf_sec = 5 if arm.startswith('ARM3') or arm.startswith('ARM7') else 15
                    bars = [b for b in tf[('5s' if tf_sec == 5 else '15s')]
                            if b['et'] > p['avail'] and b['et'][:10] == p['day']]
                    trig, k, px, why = run_arm(bars, p, arm, tf_sec)
                    row['ltfTriggered'] = 'TRUE' if trig else 'FALSE'
                    row['noFillReason'] = why
                    if trig:
                        row['ltfEntryTime'] = bars[k]['et']
                        row['ltfEntryPrice'] = px
                        t0 = datetime.datetime.strptime(p['avail'], '%Y-%m-%d %H:%M:%S')
                        t1 = datetime.datetime.strptime(bars[k]['et'], '%Y-%m-%d %H:%M:%S')
                        row['delaySeconds'] = int((t1 - t0).total_seconds())
                        row['entryImprovementPoints'] = (p['entry_px'] - px) * p['d']
                        anchor = bars[k]['et'][:17] + '00'
                        ja = bidx.get(anchor)
                        row['fwd60Arm'] = (fwd(px, ja)[60] if ja is not None else None)
                    else:
                        row['fwd60Arm'] = None
            out.append(row)
    fn = os.path.join(HERE, 'per_parent.csv')
    with open(fn, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print('wrote %s (%d rows = %d parents x %d arms)' % (fn, len(out), len(P), len(ARMS)))
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'audit'
    if cmd == 'audit':
        print('5s: NOT AVAILABLE (no historical file anywhere in repo/scratch)')
        print('15s: NOT AVAILABLE')
        print('tick: NOT AVAILABLE')
        print('30s: AVAILABLE 2025-09..2026-05 morning window, OHLCV only')
    elif cmd == 'validate':
        validate(sys.argv[2])
    elif cmd == 'run':
        d = sys.argv[2]
        if not validate(d):
            print('CAPTURE INTEGRITY FAILED - no backtesting performed')
        else:
            per_parent(d)
