import pandas as pd, numpy as np
def build(b, dev_mask):
    """Binary predicate pool. Continuous thresholds come from DEV ONLY - no leakage."""
    P={}
    def num(c): return pd.to_numeric(b[c],errors='coerce').to_numpy(float)
    def q(c,p):
        v=num(c); return np.nanquantile(v[dev_mask],p)
    for col,vals in [('trendState',None),('volState',None),('rangeState',None),
                     ('emaStack',None),('interaction',None),('seqState',None),('barDir',None)]:
        s=b[col].astype(str)
        for v in s.value_counts().index[:6]:
            if v in ('UNKNOWN','nan'): continue
            P['%s=%s'%(col.replace('State',''),v)]=(s==v).to_numpy()
    tb=b.timeBucket.astype(str)
    P['t=RTH_OPEN']=tb.isin(['T0930_0945','T0945_1000','T1000_1015']).to_numpy()
    P['t=RTH_AM']=tb.isin(['T1015_1030','T1030_1045','T1045_1100','T1100_1130']).to_numpy()
    P['t=RTH_MID']=tb.isin(['T1130_1300']).to_numpy()
    P['t=RTH_PM']=tb.isin(['T1300_1600']).to_numpy()
    P['t=OVERNIGHT']=(tb=='OVERNIGHT').to_numpy()
    for c,lab in [('distVwapAtr','vwap'),('distEma20Atr','e20'),('distEma200Atr','e200')]:
        v=num(c); P['%s<-1'%lab]=v<-1.0; P['%s>+1'%lab]=v>1.0
    v=num('ema200SlopePts'); P['slope>q75']=v>q('ema200SlopePts',.75); P['slope<q25']=v<q('ema200SlopePts',.25)
    v=num('compressionRatio'); P['comp<q25']=v<q('compressionRatio',.25); P['comp>q75']=v>q('compressionRatio',.75)
    v=num('atr'); P['atr<q25']=v<q('atr',.25); P['atr>q75']=v>q('atr',.75)
    v=np.abs(num('distLevelAtr')); P['atLevel']=v<0.25
    v=num('bodyPctOfRange'); P['body>70']=v>70; P['body<30']=v<30
    v=num('testNumberToday'); P['test>=2']=v>=2
    v=num('levelAgeMinutes'); P['oldLevel']=v>q('levelAgeMinutes',.75)
    v=num('pullbackPct'); P['pull>q75']=v>q('pullbackPct',.75)
    # drop degenerate predicates
    keep={}
    for k,m in P.items():
        m=np.nan_to_num(m,nan=False).astype(bool)
        r=m[dev_mask].mean()
        if 0.01<r<0.85: keep[k]=m
    return keep
