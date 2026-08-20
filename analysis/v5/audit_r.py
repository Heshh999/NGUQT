import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl').reset_index(drop=True)
N=len(b); K=80
c=b.close.to_numpy(float); h=b.high.to_numpy(float); l=b.low.to_numpy(float)
b1r=pd.to_numeric(b.barToLong_1R,errors='coerce').to_numpy(float)
bstop=pd.to_numeric(b.barToStopLong,errors='coerce').to_numpy(float)
print("barToLong_1R  : -1 means never hit -> %.2f%% never"%((b1r<0).mean()*100))
print("barToStopLong : %.2f%% never"%((bstop<0).mean()*100))
print("value 0 present? b1r:",int((b1r==0).sum()),"bstop:",int((bstop==0).sum()))
# candidate R definitions (distance below close for a long stop)
cands={}
for nm in ['stopMicroSwingLong','stopBarExtremeLong','stopLevelBufferLong','stopAtrLong']:
    if nm in b.columns: cands[nm]=pd.to_numeric(b[nm],errors='coerce').to_numpy(float)
print("\ncandidate stop-distance columns (points below entry):")
for nm,v in cands.items(): print("   %-22s median %.3f  min %.2f  max %.2f  nonnull %.1f%%"%(nm,np.nanmedian(v),np.nanmin(v),np.nanmax(v),np.isfinite(v).mean()*100))
# test on a contiguous slice to keep it fast
S=slice(200000,400000)
idx=np.arange(N)[S]
def first_hit(level,arr,up):
    """first k in 1..K where arr[t+k] >= level (up) or <= level (down); -1 if none"""
    out=np.full(len(idx),-1.0)
    for k in range(1,K+1):
        j=idx+k
        ok=(out<0)&(j<N)
        if up: hit=ok&(arr[j]>=level)
        else:  hit=ok&(arr[j]<=level)
        out[hit]=k
    return out
print("\nmatching barToStopLong against each candidate R:")
for nm,v in cands.items():
    lvl=c[idx]-v[idx]
    got=first_hit(lvl,l,False)
    m=np.isfinite(bstop[idx])&np.isfinite(lvl)
    print("   %-22s exact %.2f%%"%(nm,(got[m]==bstop[idx][m]).mean()*100))
print("\nmatching barToLong_1R (target = close + R) against each candidate R:")
for nm,v in cands.items():
    lvl=c[idx]+v[idx]
    got=first_hit(lvl,h,True)
    m=np.isfinite(b1r[idx])&np.isfinite(lvl)
    print("   %-22s exact %.2f%%"%(nm,(got[m]==b1r[idx][m]).mean()*100))
