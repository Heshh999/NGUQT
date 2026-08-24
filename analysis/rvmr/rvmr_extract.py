#!/usr/bin/env python3
# ======================================================================
# RVMR-V1 - extract per-bar 1m OHLCV from the V3 event-expanded asset
# ======================================================================
# The V3 export (scratchpad/run151629, 86 monthly files, audited in
# docs/V5_PHASE0_AUDIT.md) repeats each bar ~2.01x, once per nearby
# reference level. This extractor reduces it to ONE row per bar:
# first-wins on the bar timestamp, timeframe '1m' only, warmup excluded.
# Pure reduction - no bar is created, merged, split or interpolated.
#
# Output: one CSV per calendar year, et,open,high,low,close,volume
# (et = the V3 stamp, convention resolved by the basis check, not here).
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, csv, glob, sys

SRC = ('/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce'
       '/scratchpad/run151629')
OUT = ('/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce'
       '/scratchpad/rvmr_1m')

os.makedirs(OUT, exist_ok=True)
files = sorted(glob.glob(os.path.join(SRC, 'V3_1m_*.csv')))
print('source files: %d' % len(files))

wtr, wyear = None, None
total, dupes, warm, nonbar = 0, 0, 0, 0
conflicts = 0
for f in files:
    seen = {}
    with open(f, newline='') as fh:
        r = csv.reader(fh)
        h = next(r)
        i = {c: k for k, c in enumerate(h)}
        for row in r:
            if len(row) != len(h):
                continue
            if row[i['timeframe']] != '1m':
                nonbar += 1
                continue
            if row[i['isWarmup']] == 'TRUE':
                warm += 1
                continue
            et = row[i['date']] + ' ' + row[i['timeEt']]
            bar = (row[i['open']], row[i['high']], row[i['low']],
                   row[i['close']], row[i['volume']])
            if et in seen:
                dupes += 1
                if seen[et] != bar:
                    conflicts += 1
                    if conflicts <= 5:
                        print('  CONFLICT %s  %s vs %s' % (et, seen[et], bar))
                continue
            seen[et] = bar
    for et in sorted(seen):
        y = et[:4]
        if y != wyear:
            if wtr:
                wtr.close()
            wtr = open(os.path.join(OUT, 'rvmr_1m_%s.csv' % y), 'a', newline='')
            if os.path.getsize(os.path.join(OUT, 'rvmr_1m_%s.csv' % y)) == 0:
                wtr.write('et,open,high,low,close,volume\n')
            wyear = y
        o, hi, lo, c, v = seen[et]
        wtr.write('%s,%s,%s,%s,%s,%s\n' % (et, o, hi, lo, c, v))
        total += 1
    print('  %s  bars %d' % (os.path.basename(f)[-11:-4], len(seen)))
if wtr:
    wtr.close()
print('TOTAL bars %d   duplicate rows folded %d   conflicting %d   '
      'warmup dropped %d   non-1m %d' % (total, dupes, conflicts, warm, nonbar))
if conflicts:
    sys.exit('ABORT: duplicated bars DISAGREE - resolve before any study')
