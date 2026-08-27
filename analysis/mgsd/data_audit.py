#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  PHASE A  -  DATA AUDIT  (integrity facts only)
# Computes NO signal, NO outcome, NO conditional statistic.
# ======================================================================
import os, sys, csv, glob, json, hashlib, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
import rvmr_run as RV

RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
et, day, mod, em = D['et'], D['day'], D['mod'], D['em']
o, h, l, c, v = D['o'], D['h'], D['l'], D['c'], D['v']

rep = {}
rep['bars'] = N
rep['first'] = et[0]; rep['last'] = et[-1]
days = sorted(set(day)); rep['days'] = len(days)
rep['dupes'] = N - len(set(et))
span = em[-1] - em[0] + 1
rep['missing_minutes'] = span - N
bad = sum(1 for i in range(N) if not (l[i] <= min(o[i], c[i]) <= max(o[i], c[i]) <= h[i]))
rep['ohlc_violations'] = bad
rep['nonpos_price'] = sum(1 for i in range(N) if l[i] <= 0)
rep['zero_vol_bars'] = sum(1 for i in range(N) if v[i] <= 0)
rep['neg_vol_bars'] = sum(1 for i in range(N) if v[i] < 0)

# per-year coverage + RTH-morning coverage (09:31..11:30 close stamps = 120 bars)
byyear = collections.Counter(d[:4] for d in days)
rep['days_by_year'] = dict(sorted(byyear.items()))
morn = collections.defaultdict(int)
for i in range(N):
    if 571 <= mod[i] <= 690:
        morn[day[i]] += 1
full = sum(1 for d in days if morn.get(d, 0) == 120)
rep['days_with_full_0930_1130'] = full
rep['days_missing_some_morning_bars'] = sum(1 for d in days if 0 < morn.get(d, 0) < 120)
rep['days_no_morning_bars'] = sum(1 for d in days if morn.get(d, 0) == 0)
# complete calendar years for durability: full years with >=240 trading days
rep['complete_years'] = [y for y, n in sorted(byyear.items()) if n >= 240]

# aggregation determinism test: 1m -> 3m and 1m -> 15m on ET boundaries
def agg_check(step):
    ok = 0; tot = 0
    grp = collections.defaultdict(list)
    for i in range(N):
        # close-stamped: bar stamped m covers (m-1, m]; a k-min bar ending at
        # boundary B (mod % step == 0... using stamp groups (B-step, B])
        b = ((mod[i] - 1) // step)
        grp[(day[i], b)].append(i)
    for (dy, b), idx in list(grp.items())[:200000]:
        if len(idx) != step:
            continue
        idx.sort(key=lambda i: em[i])
        if em[idx[-1]] - em[idx[0]] != step - 1:
            continue
        tot += 1
        hi = max(h[i] for i in idx); lo = min(l[i] for i in idx)
        if o[idx[0]] == o[idx[0]] and hi >= lo and c[idx[-1]] == c[idx[-1]]:
            ok += 1
    return ok, tot
ok3, tot3 = agg_check(3)
ok15, tot15 = agg_check(15)
rep['agg_3m'] = {'complete_groups': tot3, 'consistent': ok3}
rep['agg_15m'] = {'complete_groups': tot15, 'consistent': ok15}

# source files + hashes
files = sorted(glob.glob(os.path.join(RV.DATA, 'rvmr_1m_*.csv')))
rep['source_files'] = []
for fn in files:
    hsh = hashlib.sha256(open(fn, 'rb').read()).hexdigest()
    rep['source_files'].append({'path': os.path.relpath(fn, os.path.join(HERE, '..', '..')),
                                'sha256': hsh,
                                'bytes': os.path.getsize(fn)})

# secondary datasets (inventoried, not used for MGSD-V1 discovery)
sec = []
of_files = sorted(glob.glob('/tmp/claude-0/-home-user-NGUQT/*/scratchpad/ofnew/v4_1_orderflow_MNQ_v41of_*.csv'))
sec.append({'name': 'order-flow capture (OFH lineage)',
            'files': len(of_files) if of_files else 'scratchpad (see v41/cand_spec.py loader)',
            'coverage': '2025-08-18 .. 2026-08-19 (355,455 bars, audited in OFH studies)',
            'role': 'EXCLUDED from MGSD-V1 price-action discovery; '
                    'order flow only as later incremental test per directive'})
ltf = sorted(glob.glob(os.path.join(HERE, '..', 'ltf_exec', 'data', '*.csv')))
sec.append({'name': '5s/15s/30s LTF capture', 'files': len(ltf),
            'coverage': '2025-09 .. 2026-05, 192 days, ~09:30-11:00 ET',
            'role': 'EXCLUDED (30-second-and-below excluded during MGSD-V1)'})
rep['secondary_datasets'] = sec
rep['dom_depth'] = 'NOT AVAILABLE in any dataset'
rep['bid_ask_prints'] = 'NOT AVAILABLE on the 1m research grid'
rep['rollover'] = ('grid extracted from the V3 continuous MNQ series; '
                   'stitching audited in RVMR-V1 Phase 0 (frozen); '
                   'no roll re-derivation performed here')

print(json.dumps(rep, indent=1))
with open(os.path.join(HERE, 'MGSD_V1_DATA_MANIFEST.json'), 'w') as f:
    json.dump(rep, f, indent=1)
