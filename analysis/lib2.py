import pandas as pd, numpy as np
rng=np.random.default_rng(20260819)
def est(y,days,B=2000):
    """POINT ESTIMATE = pooled mean (every trade is a trade).
       STANDARD ERROR = block bootstrap resampling SESSION DAYS, which is where
       the dependence lives. Using the mean-of-daily-means as the point estimate
       equal-weights days and, with wildly unequal events per day and heavy
       tails, can put the estimate outside the range of its own subgroups."""
    g=pd.DataFrame({'y':y,'d':days}).dropna()
    if len(g)<50: return np.nan,np.nan,np.nan,0,0
    mu=float(g.y.mean())
    grp=[v.values for _,v in g.groupby('d')['y']]
    k=len(grp)
    if k<20: return mu,np.nan,np.nan,len(g),k
    idx=rng.integers(0,k,size=(B,k))
    bs=np.array([np.concatenate([grp[i] for i in row]).mean() for row in idx])
    se=float(bs.std(ddof=1))
    return mu,se,(mu/se if se>0 else np.nan),len(g),k
def diff(d,ma,mb,col,B=2000):
    a,b=d[ma],d[mb]
    Ma,Sa,_,Na,_=est(a[col],a['date'],B); Mb,Sb,_,Nb,_=est(b[col],b['date'],B)
    if np.isnan(Ma) or np.isnan(Mb) or np.isnan(Sa) or np.isnan(Sb): return None
    dd=Ma-Mb; se=np.sqrt(Sa**2+Sb**2)
    return dict(a=Ma,an=Na,b=Mb,bn=Nb,diff=dd,se=se,t=dd/se if se>0 else np.nan)
