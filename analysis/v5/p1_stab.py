import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
s=pd.read_pickle('v5/sess.pkl'); s=s[s.overnight.notna()].copy()
s['lvl']=s.c1600
# vol-normalised: points expressed relative to that day's price level (bp of index)
for k in ['overnight','rth','full','open30','close30']:
    s[k+'_bp']=s[k]/s.lvl*10000.0
print("index level: 2019 median %.0f -> 2026 median %.0f  (ratio %.2fx)"%(
    s[s.year==2019].lvl.median(),s[s.year==2026].lvl.median(),
    s[s.year==2026].lvl.median()/s[s.year==2019].lvl.median()))

def line(nm,x):
    mu,se,t,n=boot_mean(x)
    tr=pd.Series(x).dropna()
    w=tr.clip(tr.quantile(.01),tr.quantile(.99))
    print("  %-22s mean %8.3f  t %6.2f | median %8.3f | 1%%-winsor mean %8.3f | n %d"%(nm,mu,t,tr.median(),w.mean(),n))

print("\n== H6 Monday effect, dissected ==")
for lab,col in (('POINTS','rth'),('BASIS POINTS','rth_bp')):
    print(" ",lab)
    line("Monday",s[s.dow==0][col]); line("Tue-Fri",s[s.dow!=0][col])
    mu,se,t,n=boot_diff(s[s.dow==0][col],s[s.dow!=0][col]); print("    diff %.4f  t %.2f"%(mu,t))
print("\n  Monday RTH by year (points):")
for y,g in s[s.dow==0].groupby('year'):
    print("    %d  n=%3d  mean %9.2f  median %8.2f"%(y,len(g),g.rth.mean(),g.rth.median()))
print("\n  5 largest |Monday RTH| moves:")
mon=s[s.dow==0].assign(a=s[s.dow==0].rth.abs()).nlargest(5,'a')
for _,r in mon.iterrows(): print("    %s  rth %+8.2f pt  (index %.0f)"%(r.d.date(),r.rth,r.lvl))

print("\n== per-SPLIT and per-YEAR sign consistency (decision rule 3 and 4) ==")
def signs(nm,fn,pred):
    row=[]
    for sp in ['DEV','VAL','LOCKBOX']:
        row.append(fn(s[s.split==sp]))
    yr=[fn(s[s.year==y]) for y in sorted(s.year.unique())]
    ok_sp=all(np.sign(v)==pred for v in row if np.isfinite(v))
    nyr=sum(1 for v in yr if np.isfinite(v) and np.sign(v)==pred)
    print("  %-28s splits %s  -> %s |  years matching predicted sign: %d/%d %s"%(
        nm,"".join("%+9.2f"%v for v in row),"OK" if ok_sp else "FAIL",nyr,len(yr),
        "OK" if nyr>=6 else "FAIL"))
signs("H1a overnight>0",      lambda g: g.overnight.mean(), +1)
signs("H1b overnight-RTH>0",  lambda g:(g.overnight-g.rth).mean(), +1)
signs("H2  RTH<=0",           lambda g: g.rth.mean(), -1)
signs("H3  TOM-rest>0",       lambda g: g[g.tom].full.mean()-g[~g.tom].full.mean(), +1)
signs("H4  corr(on,0930)<0",  lambda g: np.corrcoef(g.overnight,g.open30)[0,1], -1)
signs("H5  1530-1600>0",      lambda g: g.close30.mean(), +1)
signs("H6  Mon-other<0",      lambda g: g[g.dow==0].rth.mean()-g[g.dow!=0].rth.mean(), -1)
