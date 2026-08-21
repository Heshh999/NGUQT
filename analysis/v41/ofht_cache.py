#!/usr/bin/env python3
# Extended bar cache for the OFH7-OFH10 TIMING family.
# Adds the order-flow diagnostic columns the earlier caches dropped, so
# entries can be RECORDED with full context (record first, filter never -
# per the research directive). No analysis happens here.
#
# NOTE the order-flow capture has NO VWAP column (that lives in the
# structure capture only), so "VWAP distance" cannot be recorded for
# these entries. Stated here rather than silently omitted.

import csv, glob, os, pickle

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
D = os.path.join(SCR, 'of2')
CACHE = os.path.join(SCR, 'of_bars3.pkl')


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


NEED = ['f_open', 'f_high', 'f_low', 'f_close', 'f_atr', 'f_isRth',
        'f_minutesToRthClose', 'f_minutesFromRthOpen', 'f_bodyPctOfRange',
        'f_relVolume', 'f_ofBarDelta', 'f_ofDeltaPct', 'f_ofTotalVolume',
        'f_ofBidVolume', 'f_ofAskVolume', 'f_ofCumDelta', 'f_ofMinDelta',
        'f_ofMaxDelta', 'f_absorptionStrengthRaw', 'f_volumePerUpTick',
        'f_volumePerDownTick', 'f_buyImbalanceCount_3x',
        'f_sellImbalanceCount_3x', 'f_stackedBuyLevels_3x',
        'f_stackedSellLevels_3x', 'f_profileReady', 'f_profilePoc',
        'f_profileVah', 'f_profileVal', 'f_distPocAtr', 'f_distVahAtr',
        'f_distValAtr']


def build():
    bars = []
    for f in sorted(glob.glob(os.path.join(D, 'v4_1_orderflow_MNQ_v41of_*.csv'))):
        with open(f, newline='') as fh:
            r = csv.reader(fh)
            h = next(r)
            i = {c: k for k, c in enumerate(h)}
            for row in r:
                if len(row) != len(h):
                    continue
                d = {}
                for c in NEED:
                    v = row[i[c]]
                    d[c[2:]] = (v == 'TRUE') if v in ('TRUE', 'FALSE') else F(v)
                if d['high'] is None or d['atr'] is None or d['close'] is None:
                    continue
                et = row[i['f_barCloseEt']]
                d['et'] = et
                d['day'] = et[:10]
                d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640
                             + int(et[8:10]) * 1440 + int(et[11:13]) * 60
                             + int(et[14:16]))
                bars.append(d)
    bars.sort(key=lambda b: b['et'])
    with open(CACHE, 'wb') as fh:
        pickle.dump(bars, fh, 2)
    return bars


def load():
    if os.path.exists(CACHE):
        with open(CACHE, 'rb') as fh:
            return pickle.load(fh)
    return build()


if __name__ == '__main__':
    B = load()
    print('cached %d bars  %s -> %s' % (len(B), B[0]['et'], B[-1]['et']))
