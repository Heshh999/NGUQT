import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl').reset_index(drop=True)
c=b.close.astype(float)
print("== EMA causality (recursive from trailing closes only) ==")
for p,col in ((9,'ema9'),(20,'ema20'),(200,'ema200')):
    f=pd.to_numeric(b[col],errors='coerce')
    rec=c.ewm(span=p,adjust=False).mean()
    d=(f-rec).abs()
    ok=(d<0.01).mean()*100
    print("   %-7s recursive match %.2f%%   median abs err %.4f"%(col,ok,d.median()))
print("\n== ATR causality ==")
atr=pd.to_numeric(b.atr,errors='coerce')
tr=pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1)
for p in (14,20):
    rec=tr.ewm(alpha=1.0/p,adjust=False).mean()
    print("   Wilder p=%d  median abs err %.4f  corr %.5f"%(p,(atr-rec).abs().median(),atr.corr(rec)))
    rec2=tr.rolling(p).mean()
    print("   SMA    p=%d  median abs err %.4f  corr %.5f"%(p,(atr-rec2).abs().median(),atr.corr(rec2)))
print("\n== posInSessRange: CAUSAL (session-to-date) vs LOOKAHEAD (whole session) ==")
p=pd.to_numeric(b.posInSessRange,errors='coerce')
print("   non-null %.2f%%  range [%.3f, %.3f]"%(p.notna().mean()*100,p.min(),p.max()))
sub=b[p.notna()].copy(); sub['p']=p[p.notna()]
g=sub.groupby('date')
causal=(sub.close-g.low.cummin())/(g.high.cummax()-g.low.cummin())
full_hi=g.high.transform('max'); full_lo=g.low.transform('min')
lookahead=(sub.close-full_lo)/(full_hi-full_lo)
for nm,v in (('CAUSAL session-to-date',causal),('LOOKAHEAD whole session',lookahead)):
    d=(sub.p-v*100).abs()
    d2=(sub.p-v).abs()
    print("   %-24s  match(x100) %.2f%%   match(x1) %.2f%%"%(nm,(d<0.5).mean()*100,(d2<0.005).mean()*100))
print("\n== relVolume ==")
rv=pd.to_numeric(b.relVolume,errors='coerce'); v=b.volume.astype(float)
for p_ in (20,50):
    rec=v/v.rolling(p_).mean()
    print("   vol / trailing SMA%d   median abs err %.4f  corr %.4f"%(p_,(rv-rec).abs().median(),rv.corr(rec)))
