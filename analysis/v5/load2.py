import pandas as pd, numpy as np, glob, os
COLS=['eventId','date','timeEt','barDir','open','high','low','close','volume','atr',
      'rangePts','bodyPctOfRange','upperWickPts','lowerWickPts',
      'distLevelAtr','interaction','seqState','testNumberToday','levelAgeMinutes','levelName',
      'distEma9Atr','distEma20Atr','distEma200Atr','distVwapAtr','ema200SlopePts','emaStack',
      'trendState','volState','rangeState','compressionRatio','pullbackPct','timeBucket',
      'distPmHighAtr','distPmLowAtr','stopMicroSwingLong','stopMicroSwingShort',
      'net_3','net_10','net_20','net_40','net_80','barsObserved']
F=sorted(glob.glob('run151629/*.csv'))
out=[]
for i,f in enumerate(F):
    d=pd.read_csv(f,usecols=COLS,low_memory=False)
    d['ab']=pd.to_numeric(d.distLevelAtr,errors='coerce').abs()
    # per bar keep the NEAREST level row - a deterministic, causal choice
    d=d.sort_values(['eventId','ab'],kind='mergesort').drop_duplicates('eventId',keep='first')
    out.append(d)
    if i%20==0: print("  %d/%d"%(i+1,len(F)),flush=True)
b=pd.concat(out,ignore_index=True)
b['dt']=pd.to_datetime(b.date+' '+b.timeEt,format='%Y-%m-%d %H:%M:%S')
b=b.sort_values('dt').reset_index(drop=True)
b['exday']=(b.dt-pd.Timedelta(hours=18)).dt.normalize()
b.to_pickle('v5/feat.pkl')
print("rows",len(b),b.dt.min(),"->",b.dt.max())
print("interaction:",b.interaction.value_counts().head(8).to_dict())
print("seqState:",b.seqState.value_counts().head(6).to_dict())
print("emaStack:",b.emaStack.value_counts().to_dict())
print("rangeState:",b.rangeState.value_counts().to_dict())
