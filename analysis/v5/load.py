import pandas as pd, numpy as np, glob, os, sys
OUT='v5/bars.pkl'
COLS=['eventId','date','timeEt','eventKind','isWarmup','open','high','low','close','volume',
      'atr','relVolume','rangePts','volState','trendState','timeBucket','posInSessRange',
      'ema9','ema20','ema200','vwap','compressionRatio',
      'net_3','net_5','net_10','net_20','net_40','net_80',
      'mfeLong_3','maeLong_3','mfeLong_20','maeLong_20','mfeLong_80','maeLong_80',
      'barToLong_1R','barToShort_1R','barToStopLong','barToStopShort',
      'barToLong_2R','barToShort_2R','barsObserved',
      'stopMicroSwingLong','stopMicroSwingShort','stopAtrLong','stopAtrShort']
def main():
    F=sorted(glob.glob('run151629/*.csv'))
    out=[]
    for i,f in enumerate(F):
        d=pd.read_csv(f,usecols=COLS,low_memory=False)
        # one row per BAR: the file repeats each bar once per nearby level
        d=d.drop_duplicates('eventId',keep='first')
        out.append(d)
        if i%12==0: print(f"  {i+1}/{len(F)} {os.path.basename(f)[-11:-4]} rows={len(d)}",flush=True)
    b=pd.concat(out,ignore_index=True)
    b['dt']=pd.to_datetime(b.date+' '+b.timeEt,format='%Y-%m-%d %H:%M:%S')
    b=b.sort_values('dt').reset_index(drop=True)
    b.to_pickle(OUT)
    print("TOTAL bars",len(b),"span",b.dt.min(),"->",b.dt.max())
main()
