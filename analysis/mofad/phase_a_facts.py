#!/usr/bin/env python3
# ======================================================================
# MOFAD-V1  Phase A  -  DATA FACTS, COUNTS AND HASHES ONLY
# No outcome, no forward return, no P&L is computed here.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv, glob, hashlib, json, os, sys

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
DEV_LAST = '2026-08-17'          # frozen DEV cap (MGSD partition, preserved)
BUF_LO, BUF_HI = '2026-08-18', '2026-08-31'   # untouched buffer

def sha(path, h=None):
    h = h or hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            h.update(ch)
    return h

def dirhash(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(os.path.basename(p).encode())
        sha(p, h)
    return h.hexdigest()

M = {}

# ---- 1. OF capture (ofnew + of2), day coverage under DEV cap --------
days, days_dev, rows = set(), set(), 0
hours = set()
for d in ('ofnew', 'of2'):
    for f in sorted(glob.glob(SCR + '/%s/v4_1_orderflow_MNQ_v41of_*.csv' % d)):
        with open(f, newline='') as fh:
            r = csv.reader(fh); hd = next(r); i = {c: k for k, c in enumerate(hd)}
            for row in r:
                if len(row) != len(hd):
                    continue
                et = row[i['f_barCloseEt']]
                dy = et[:10]
                days.add(dy); rows += 1
                if dy <= DEV_LAST:
                    days_dev.add(dy); hours.add(int(et[11:13]))
ofnew = sorted(glob.glob(SCR + '/ofnew/*.csv')); of2 = sorted(glob.glob(SCR + '/of2/v4_1_orderflow_MNQ_v41of_*.csv'))
M['of_capture'] = dict(
    files_ofnew=len(ofnew), files_of2=len(of2), rows_total=rows,
    days_total=len(days), day_min=min(days), day_max=max(days),
    days_dev_eligible=len(days_dev), dev_day_min=min(days_dev), dev_day_max=max(days_dev),
    hours_covered_dev=sorted(hours),
    buffer_days_present=sorted(d for d in days if BUF_LO <= d <= BUF_HI),
    sha256_ofnew=dirhash(ofnew), sha256_of2=dirhash(of2))

# ---- 2. RVMR 1m price extract ---------------------------------------
rv = sorted(glob.glob(SCR + '/rvmr_1m/rvmr_1m_*.csv'))
M['rvmr_1m'] = dict(files=len(rv), sha256=dirhash(rv))

# ---- 3. ES pilot (42-day 1m) ----------------------------------------
es = sorted(glob.glob(SCR + '/es_pilot/V41_LTF_ES_*.csv'))
esdays = [os.path.basename(p)[11:-4] for p in es]
flow_nonempty = 0; esrows = 0
for p in es:
    with open(p, newline='') as fh:
        r = csv.reader(fh); hd = next(r); i = {c: k for k, c in enumerate(hd)}
        for row in r:
            esrows += 1
            if row[i['bidVolume']] not in ('', None) or row[i['delta']] not in ('', None):
                flow_nonempty += 1
M['es_pilot'] = dict(files=len(es), rows=esrows, day_min=min(esdays), day_max=max(esdays),
                     flow_fields_populated_rows=flow_nonempty, sha256=dirhash(es))

# ---- 4. es_full (v4.1 ES event/structure research CSVs) -------------
ef = sorted(glob.glob(SCR + '/es_full/*.csv'))
M['es_full_events'] = dict(files=len(ef),
                           entries=len([p for p in ef if 'entries' in p]),
                           structure=len([p for p in ef if 'structure' in p]),
                           sha256=dirhash(ef))

# ---- 5. 30s ph2 exports ---------------------------------------------
p2 = sorted(glob.glob(SCR + '/ph2/V3_30s_*.csv'))
months = sorted(os.path.basename(p)[-10:-4] for p in p2)
M['s30_ph2'] = dict(files=len(p2), months=months, sha256=dirhash(p2))

json.dump(M, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phase_a_facts.json'), 'w'), indent=1)
print(json.dumps(M, indent=1))
