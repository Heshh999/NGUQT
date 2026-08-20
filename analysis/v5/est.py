import numpy as np, pandas as pd
RNG=np.random.default_rng(20260820)
COST=1.5
def boot_mean(x,B=2000):
    """POOLED mean point estimate; SE by iid bootstrap over days (each row IS a day)."""
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    n=len(x)
    if n<30: return np.nan,np.nan,np.nan,n
    mu=x.mean()
    idx=RNG.integers(0,n,size=(B,n))
    bs=x[idx].mean(axis=1)
    se=bs.std(ddof=1)
    t=mu/se if se>0 else np.nan
    return mu,se,t,n
def boot_diff(x,y,B=2000):
    """difference of two independent day-groups"""
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    y=np.asarray(y,float); y=y[np.isfinite(y)]
    if len(x)<30 or len(y)<30: return np.nan,np.nan,np.nan,len(x)+len(y)
    mu=x.mean()-y.mean()
    bx=x[RNG.integers(0,len(x),size=(B,len(x)))].mean(axis=1)
    by=y[RNG.integers(0,len(y),size=(B,len(y)))].mean(axis=1)
    se=(bx-by).std(ddof=1)
    return mu,se,(mu/se if se>0 else np.nan),len(x)+len(y)
def boot_paired(d,B=2000):
    return boot_mean(d,B)
def boot_corr(x,y,B=2000):
    m=np.isfinite(x)&np.isfinite(y); x=np.asarray(x,float)[m]; y=np.asarray(y,float)[m]
    n=len(x)
    if n<30: return np.nan,np.nan,np.nan,n
    r=np.corrcoef(x,y)[0,1]
    idx=RNG.integers(0,n,size=(B,n))
    bs=np.array([np.corrcoef(x[i],y[i])[0,1] for i in idx])
    se=bs.std(ddof=1)
    return r,se,(r/se if se>0 else np.nan),n
def two_sided_p(t):
    from math import erfc,sqrt
    return erfc(abs(t)/sqrt(2)) if np.isfinite(t) else np.nan
def bh(ps,q=0.05):
    ps=np.asarray(ps,float); n=len(ps); o=np.argsort(ps); rank=np.arange(1,n+1)
    crit=q*rank/n; passed=ps[o]<=crit
    k=np.max(np.where(passed)[0])+1 if passed.any() else 0
    out=np.zeros(n,bool)
    if k: out[o[:k]]=True
    return out,crit[np.argsort(o)]

def boot_day(y,days,B=2000):
    """POOLED mean point estimate; SE by DAY-BLOCK bootstrap (bars cluster within days)."""
    g=pd.DataFrame({'y':np.asarray(y,float),'d':np.asarray(days)}).dropna()
    if len(g)<50: return np.nan,np.nan,np.nan,0,0
    mu=float(g.y.mean())
    grp=[v.values for _,v in g.groupby('d')['y']]
    k=len(grp)
    if k<20: return mu,np.nan,np.nan,len(g),k
    sums=np.array([v.sum() for v in grp]); cnts=np.array([len(v) for v in grp])
    idx=RNG.integers(0,k,size=(B,k))
    bs=sums[idx].sum(axis=1)/cnts[idx].sum(axis=1)
    se=bs.std(ddof=1)
    return mu,se,(mu/se if se>0 else np.nan),len(g),k
