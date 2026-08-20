import pandas as pd, numpy as np
MINATR=1.0   # DATA VALIDITY: MNQ ticks in 0.25; an ATR below one tick is a
             # degenerate measurement, not a volatility estimate. 142 such rows
             # (0.078%) carried a y-sum larger than the whole dataset's.
def load():
    d=pd.read_pickle('struct.pkl')
    d['dt']=pd.to_datetime(d['date']+' '+d['timeEt'])
    d=d[d.eventKind=='BREAK'].copy()
    d=d[d.minutesObserved<=400]                  # window did not span a closure
    d=d[d['net_240m'].notna()]
    d=d[d.tfAtr>=MINATR]                         # validity filter
    d['y']=d['net_240m']/d['tfAtr']
    d['y60']=d['net_60m']/d['tfAtr']
    # winsorise within timeframe: heavy tails remain even after the filter
    for c in ['y','y60']:
        d[c+'w']=d.groupby('tf')[c].transform(
            lambda s: s.clip(s.quantile(.01),s.quantile(.99)))
    d['contw']=d.groupby('tf')['contMaxAtr'].transform(
            lambda s: s.clip(s.quantile(.01),s.quantile(.99)))
    d['split']=np.where(d.dt<'2023-01-01','DEV',np.where(d.dt<'2025-01-01','VAL','OOS'))
    return d
def clustered(y,c):
    g=pd.DataFrame({'y':y,'c':c}).dropna()
    if len(g)<50: return np.nan,np.nan,np.nan,0,0
    m=g.groupby('c')['y'].mean(); n=len(m)
    if n<20: return np.nan,np.nan,np.nan,len(g),n
    mu=float(m.mean()); se=float(m.std(ddof=1)/np.sqrt(n))
    return mu,se,(mu/se if se>0 else np.nan),len(g),n
def cmp2(d,ma,mb,col):
    a,b=d[ma],d[mb]
    Ma,Sa,Ta,Na,Ca=clustered(a[col],a['date']); Mb,Sb,Tb,Nb,Cb=clustered(b[col],b['date'])
    if np.isnan(Ma) or np.isnan(Mb): return None
    dif=Ma-Mb; se=np.sqrt(Sa**2+Sb**2)
    return dict(a=Ma,an=Na,b=Mb,bn=Nb,diff=dif,se=se,t=(dif/se if se>0 else np.nan))
