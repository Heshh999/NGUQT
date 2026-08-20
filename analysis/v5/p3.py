import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
d=pd.read_pickle('V4LAB/flow.pkl').copy()
d['dt']=pd.to_datetime(d.date.astype(str)+' '+d.timeEt.astype(str))
d=d.sort_values('dt').reset_index(drop=True)
print("flow bars %d  %s -> %s  days %d"%(len(d),d.dt.min(),d.dt.max(),d.date.nunique()))
# forward returns built from THIS file's own close series (the export carries only backward columns)
c=d.close.to_numpy(float); n=len(d)
for K in (20,):
    f=np.r_[c[K:]-c[:-K],np.full(K,np.nan)]
    d['net_%d'%K]=f
# a forward window must not span a session break: invalidate where t+K is a different exchange day
ex=(d.dt - pd.Timedelta(hours=18)).dt.normalize()
d['exday']=ex
same=np.r_[ (ex.values[20:]==ex.values[:-20]), np.zeros(20,bool)]
d.loc[~same,'net_20']=np.nan
print("forward windows voided for crossing an exchange day: %d (%.2f%%)"%((~same).sum(),100*(~same).mean()))
COST=1.5
def rep(tag,mask,pred,col='net_20',sub=None):
    y=d.loc[mask,col] if sub is None else sub
    mu,se,t,nn,k=boot_day(y,d.loc[mask,'exday'])
    print("  %-46s n=%7d days=%3d  gross %+7.4f  se %6.4f  t %+6.2f  net %+7.4f  [pred %s]"%(
        tag,nn,k,mu,se,t,mu-COST,pred))
    return mu,se,t,nn
print("\n"+"="*100); print("P3  ORDER FLOW AS A PRIMARY SIGNAL   (outcome = net_20, index points, MNQ)"); print("="*100)
R={}
q9=d.barDelta.quantile(0.90)
R['H7']=rep("H7 top-decile barDelta -> positive",d.barDelta>=q9,"+")
m8=(d.newHigh20==True)&(d.cumDeltaChange20<0)
R['H8']=rep("H8 new 20-bar high on negative cum-delta -> negative",m8,"-")
d['imb']=d.buyImbalanceCount-d.sellImbalanceCount
qi9=d.imb.quantile(0.90); qi1=d.imb.quantile(0.10)
a=rep("H9 top-decile buy-sell imbalance",d.imb>=qi9,"+")
b=rep("H9 bottom-decile buy-sell imbalance",d.imb<=qi1,"-")
R['H9']=(a[0]-b[0],np.nan,np.nan,a[3]+b[3])
m=np.isfinite(d.imb)&np.isfinite(d.net_20)
print("  %-46s r=%+.4f"%("H9 correlation(imbalance, net_20)",np.corrcoef(d.imb[m],d.net_20[m])[0,1]))
d['pocdisp']=d.close-d.pocPrice
qp9=d.pocdisp.quantile(0.90)
R['H10']=rep("H10 close far above POC -> reversion",d.pocdisp>=qp9,"-")
print("\n  baseline (all bars):")
rep("   unconditional net_20",pd.Series(True,index=d.index),"n/a")
import pickle; pickle.dump(R,open('v5/p3_res.pkl','wb'))
