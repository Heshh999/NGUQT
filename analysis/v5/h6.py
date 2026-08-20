import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
s=pd.read_pickle('v5/sess.pkl'); s=s[s.overnight.notna()].copy()
s['bp']=s.rth/s.c1600*10000
NAMES=['Mon','Tue','Wed','Thu','Fri']
print("="*96); print("EXPLORATORY - NOT PART OF THE CONFIRMATORY FAMILY, NOT ELIGIBLE FOR A DECISION"); print("="*96)
print("\nRTH return by weekday (09:30->16:00), all 5 days shown so Monday is seen in context:")
print("  %-5s %5s %10s %8s %10s %10s %10s"%("day","n","mean pt","t","median","winsor 1%","mean bp"))
for i,nm in enumerate(NAMES):
    g=s[s.dow==i]; mu,se,t,n=boot_mean(g.rth)
    w=g.rth.clip(g.rth.quantile(.01),g.rth.quantile(.99))
    print("  %-5s %5d %10.3f %8.2f %10.3f %10.3f %10.3f"%(nm,len(g),mu,t,g.rth.median(),w.mean(),g.bp.mean()))
print("\n  If all five days had been tested rather than the one pre-registered, the largest")
print("  |t| among them would be the number to correct for. It is %.2f."%max(abs(boot_mean(s[s.dow==i].rth)[2]) for i in range(5)))

print("\nTradeable form: long 1 MNQ at the 09:29 close, flat at 16:00, MONDAYS ONLY")
mon=s[s.dow==0]
mu,se,t,n=boot_mean(mon.rth)
print("  gross %+.3f pt   net(-1.5) %+.3f pt   t %.2f   n %d days"%(mu,mu-1.5,t,n))
print("  per contract: $%.2f gross, $%.2f net per Monday  ->  $%.0f total over the sample"%(mu*2,(mu-1.5)*2,(mu-1.5)*2*n))
print("  win rate %.2f%%   worst day %+.2f   best day %+.2f"%(100*(mon.rth>0).mean(),mon.rth.min(),mon.rth.max()))
print("  max drawdown of the daily equity curve: %.1f pt"%((mon.rth-1.5).cumsum().cummax()-(mon.rth-1.5).cumsum()).max())

print("\n  by split:")
for sp in ['DEV','VAL','LOCKBOX']:
    g=mon[mon.split==sp]; m,_,tt,_=boot_mean(g.rth)
    print("    %-8s n=%3d  gross %+8.3f  t %5.2f  net %+8.3f"%(sp,len(g),m,tt,m-1.5))
print("\n  by year:")
for y,g in mon.groupby('year'):
    m,_,tt,_=boot_mean(g.rth) if len(g)>=30 else (g.rth.mean(),0,np.nan,0)
    print("    %d n=%3d  gross %+8.2f  median %+7.2f  win%% %5.1f"%(y,len(g),g.rth.mean(),g.rth.median(),100*(g.rth>0).mean()))

print("\n  is it reversal of the weekend move? corr(Monday overnight, Monday RTH) = %+.4f"%(
    np.corrcoef(mon.overnight,mon.rth)[0,1]))
neg=mon[mon.overnight<0]; pos=mon[mon.overnight>=0]
print("    after a DOWN weekend (n=%d): RTH %+.2f pt"%(len(neg),neg.rth.mean()))
print("    after an UP weekend  (n=%d): RTH %+.2f pt"%(len(pos),pos.rth.mean()))
