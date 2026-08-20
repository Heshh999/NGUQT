import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
s=pd.read_pickle('v5/sess.pkl'); s=s[s.overnight.notna()].copy()
print("== H1 dissected: is the overnight 'edge' anything but a longer window? ==")
ON_H=17.5; RTH_H=6.5    # 16:00->09:29 is 17.5h ; 09:30->16:00 is 6.5h
mo,_,to,_=boot_mean(s.overnight); mr,_,tr,_=boot_mean(s.rth)
print("  overnight  mean %+7.3f pt over %.1f h  ->  %+6.4f pt/hour   t=%.2f"%(mo,ON_H,mo/ON_H,to))
print("  RTH        mean %+7.3f pt over %.1f h  ->  %+6.4f pt/hour   t=%.2f"%(mr,RTH_H,mr/RTH_H,tr))
print("  per-hour drift is %s during RTH"%("HIGHER" if mr/RTH_H>mo/ON_H else "HIGHER overnight"))
tot=s.full.sum()
print("\n  total index move captured over %d days: %.0f pt"%(len(s),tot))
print("  of which overnight %.0f pt (%.1f%%), RTH %.0f pt (%.1f%%)"%(
    s.overnight.sum(),100*s.overnight.sum()/tot,s.rth.sum(),100*s.rth.sum()/tot))
print("  buy-and-hold over the same span: %.0f pt"%(s.c1600.iloc[-1]-s.c1600.iloc[0]))
print("\n  H1a net of 1.5pt cost, per day: %+.3f pt  -> $%.2f on 1 MNQ"%(mo-1.5,(mo-1.5)*2))
print("  H1a is a LONG-ONLY position in a market that rose %.2fx. It is beta, not alpha,"%(s.c1600.iloc[-1]/s.c1600.iloc[0]))
print("  unless it beats RTH per unit of exposure - which is H1b.")

print("\n== H4 dissected: is a -0.0985 correlation tradeable? ==")
r,se,t,n=boot_corr(s.overnight.values,s.open30.values)
print("  r=%.4f  t=%.2f  r^2=%.4f  (explains %.2f%% of 09:30-10:00 variance)"%(r,t,r*r,100*r*r))
# the implied rule: fade the overnight move for the first 30 minutes of RTH
sig=-np.sign(s.overnight)
pnl=sig*s.open30
mu,sd,tt,nn=boot_mean(pnl)
print("  fade-the-overnight, 09:29 -> 10:00, GROSS  mean %+.4f pt  t %.2f  n %d"%(mu,tt,nn))
print("                                       NET (-1.5pt) %+.4f pt/day"%(mu-1.5))
print("  win rate %.2f%%   median %+.3f pt"%(100*(pnl>0).mean(),pnl.median()))
for sp in ['DEV','VAL','LOCKBOX']:
    g=s[s.split==sp]; p=-np.sign(g.overnight)*g.open30
    m,_,tq,_=boot_mean(p); print("     %-8s gross %+7.3f  t %5.2f  net %+7.3f"%(sp,m,tq,m-1.5))
