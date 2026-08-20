import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl')
n=len(b)
print("bars",n)
c=b.close.to_numpy(float); h=b.high.to_numpy(float); l=b.low.to_numpy(float); o=b.open.to_numpy(float)
def rmse_match(a,bb,tol=1e-6):
    m=np.isfinite(a)&np.isfinite(bb)
    if m.sum()==0: return 0.0,0
    return float(np.mean(np.abs(a[m]-bb[m])<=tol)),int(m.sum())

for K in (3,20,80):
    net=pd.to_numeric(b['net_%d'%K],errors='coerce').to_numpy(float)
    cands={
      'close[t+K]-close[t]'  : np.r_[c[K:]-c[:-K], np.full(K,np.nan)],
      'close[t+K]-open[t+1]' : np.r_[c[K:]-o[1:n-K+1], np.full(K,np.nan)],
      'close[t+K]-open[t]'   : np.r_[c[K:]-o[:-K],  np.full(K,np.nan)],
    }
    print("\n== net_%d =="%K)
    for name,v in cands.items():
        f,cnt=rmse_match(net,v)
        print(f"   {name:24s} exact-match {f*100:6.2f}%  (n={cnt})")

# MFE / MAE
for K in (3,20):
    mfe=pd.to_numeric(b['mfeLong_%d'%K],errors='coerce').to_numpy(float)
    mae=pd.to_numeric(b['maeLong_%d'%K],errors='coerce').to_numpy(float)
    # rolling forward max of high over t+1..t+K, and min low
    sh=pd.Series(h); sl=pd.Series(l)
    fmax=sh.iloc[::-1].rolling(K,min_periods=K).max().iloc[::-1].shift(-1).to_numpy(float)
    fmin=sl.iloc[::-1].rolling(K,min_periods=K).min().iloc[::-1].shift(-1).to_numpy(float)
    fmax0=sh.iloc[::-1].rolling(K+1,min_periods=K+1).max().iloc[::-1].to_numpy(float)
    fmin0=sl.iloc[::-1].rolling(K+1,min_periods=K+1).min().iloc[::-1].to_numpy(float)
    print("\n== mfeLong_%d / maeLong_%d =="%(K,K))
    for name,v in {'max(high[t+1..t+K])-close[t]':fmax-c,'max(high[t..t+K])-close[t]':fmax0-c}.items():
        f,cnt=rmse_match(mfe,v); print(f"   MFE {name:32s} {f*100:6.2f}%")
    for name,v in {'close[t]-min(low[t+1..t+K])':c-fmin,'close[t]-min(low[t..t+K])':c-fmin0}.items():
        f,cnt=rmse_match(mae,v); print(f"   MAE {name:32s} {f*100:6.2f}%")

# end-of-history truncation
bo=pd.to_numeric(b.barsObserved,errors='coerce')
print("\n== barsObserved ==")
print("  overall value counts:",bo.value_counts().head(5).to_dict())
print("  last 100 bars:",bo.tail(100).value_counts().to_dict())
print("  min:",bo.min())
print("\nisWarmup:",b.isWarmup.value_counts().to_dict())
print("eventKind:",b.eventKind.value_counts().to_dict())
