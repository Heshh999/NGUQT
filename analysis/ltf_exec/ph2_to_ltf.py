#!/usr/bin/env python3
# ======================================================================
# ph2_to_ltf.py - convert the ALREADY-VALIDATED genuine 30s history into
# the LTF engine's input format. Pure reformatting: no bar is created,
# merged, split or interpolated. Every row is a real captured 30s bar.
# ======================================================================
import os, sys, csv, glob, collections
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'..','v41'))
import red_lib as R

OUT=os.path.join(HERE,'data')
os.makedirs(OUT,exist_ok=True)
HDR=('timestampET,instrument,contract,timeframe,open,high,low,close,volume,'
     'bidVolume,askVolume,delta,deltaPercent,parentCandidate,parentEventId,'
     'parentDirection,parentAvailableTime,parentEntryTime,parentEntryPrice,'
     'parentATR,fvgLow,fvgHigh,structuralInvalidation,parentStillValid,engineVersion')
byday=collections.defaultdict(list)
seen=set()          # first-wins dedupe, same rule as canonical load_merged
n30=n1=0; ndup=0
for f in sorted(glob.glob(R.SCR+'/ph2/*.csv')):
    m=f.split('_')[-1][:-4]
    if not ('202509'<=m<='202605'): continue
    for r in csv.DictReader(open(f)):
        if r.get('isWarmup')=='TRUE': continue
        tf=r['timeframe']
        if tf not in ('30s','1m'): continue
        et='%s %s'%(r['date'],r['timeEt'])
        if (et,tf) in seen:
            ndup+=1; continue
        seen.add((et,tf))
        byday[r['date']].append((et,tf,r['open'],r['high'],r['low'],r['close'],r['volume']))
        if tf=='30s': n30+=1
        else: n1+=1
for day,rows in byday.items():
    rows.sort()
    p=os.path.join(OUT,'V41_LTF_MNQ_%s.csv'%day.replace('-',''))
    with open(p,'w',newline='') as fh:
        fh.write(HDR+'\n')
        for et,tf,o,h,l,c,v in rows:
            fh.write('%s,MNQ,,%s,%s,%s,%s,%s,%s,,,,,,,,,,,,,,,,GENUINE-PH2-30S\n'
                     %(et,tf,o,h,l,c,v))
print('converted %d genuine 30s bars and %d 1m bars across %d days '
      '(%d identical duplicate rows dropped, first-wins) -> %s'
      %(n30,n1,len(byday),ndup,OUT))
