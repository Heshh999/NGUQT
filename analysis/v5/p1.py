import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5')
from est import *
s=pd.read_pickle('v5/sess.pkl')
s=s[s.overnight.notna()].copy()
FULL=s
HALF=s[s.rth_bars>=300]
def report(tag,s):
    print("\n"+"="*74); print("P1 EXOGENOUS CLOCK & CALENDAR  --",tag,"  n_days=%d"%len(s)); print("="*74)
    R={}
    mu,se,t,n=boot_mean(s.overnight);      R['H1a']=(mu,se,t,n,'overnight mean > 0')
    mu,se,t,n=boot_paired(s.overnight-s.rth); R['H1b']=(mu,se,t,n,'overnight - RTH > 0')
    mu,se,t,n=boot_mean(s.rth);            R['H2']=(mu,se,t,n,'RTH mean <= 0')
    mu,se,t,n=boot_diff(s[s.tom].full,s[~s.tom].full); R['H3']=(mu,se,t,n,'turn-of-month - rest > 0')
    r,se,t,n=boot_corr(s.overnight.values,s.open30.values); R['H4']=(r,se,t,n,'corr(overnight,0930-1000) < 0')
    mu,se,t,n=boot_mean(s.close30);        R['H5']=(mu,se,t,n,'1530-1600 mean > 0')
    mu,se,t,n=boot_diff(s[s.dow==0].rth,s[s.dow!=0].rth); R['H6']=(mu,se,t,n,'Monday RTH - other RTH < 0')
    print("%-5s %-32s %10s %8s %8s %8s"%("id","hypothesis","effect","se","t","n"))
    for k,(mu,se,t,n,lab) in R.items():
        print("%-5s %-32s %10.4f %8.4f %8.2f %8d"%(k,lab,mu,se,t,n))
    print("\n  units: index points per contract per day, GROSS.  cost 1.5pt assumed, applied below.")
    print("  net of one round turn:  overnight %.4f   RTH %.4f   1530-1600 %.4f"%(
        s.overnight.mean()-COST, s.rth.mean()-COST, s.close30.mean()-COST))
    return R
Rf=report("PRE-REGISTERED, all RTH dates",FULL)
Rh=report("post-freeze sensitivity, half-days (<300 RTH bars) excluded",HALF)
import pickle; pickle.dump({'full':Rf,'half':Rh},open('v5/p1_res.pkl','wb'))
