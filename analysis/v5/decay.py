import pandas as pd, numpy as np, pickle, sys
sys.path.insert(0,'v5'); from preds import build; from est import boot_day
b=pd.read_pickle('v5/feat.pkl')
obs=pd.to_numeric(b.barsObserved,errors='coerce').to_numpy(float); base=obs>=80
dt=b.dt.to_numpy()
dev=base&(b.dt<'2023-01-01').to_numpy()
val=base&((b.dt>='2023-01-01')&(b.dt<'2025-01-01')).to_numpy()
lock=base&(b.dt>='2025-01-01').to_numpy()
names,cbs,idxs,HOR=pickle.load(open('v5/qual.pkl','rb'))
best=np.load('v5/best_real.npy'); meta=pickle.load(open('v5/meta_real.pkl','rb'))
P=build(b,dev)
day=b.exday.to_numpy()
NET={k:pd.to_numeric(b['net_%d'%k],errors='coerce').to_numpy(float) for k in HOR}
order=np.argsort(-best)[:50]
print("Top 50 DEV conjunctions carried forward, GROSS points per trade")
print("%-52s %4s %3s %9s %9s %9s %7s"%("conjunction","K","d","DEV","VAL","LOCKBOX","VAL t"))
rows=[]
for rank,i in enumerate(order):
    cb=cbs[i]; K,d,nn=meta[i]
    m=np.ones(len(b),bool)
    for j in cb: m&=P[names[j]]
    y=d*NET[K]
    r={}
    for lab,sel in (('DEV',dev),('VAL',val),('LOCK',lock)):
        mm=m&sel
        r[lab]=np.nanmean(y[mm]) if mm.sum()>20 else np.nan
        r[lab+'_n']=int(mm.sum())
    mv=m&val
    mu,se,t,N,kk=boot_day(y[mv],day[mv]) if mv.sum()>50 else (np.nan,)*5
    rows.append(dict(c=" & ".join(names[j] for j in cb),K=K,d=d,**r,valt=t))
    if rank<15:
        print("%-52s %4d %3d %9.3f %9.3f %9.3f %7.2f"%(rows[-1]['c'],K,d,r['DEV'],r['VAL'],r['LOCK'],t if t==t else np.nan))
df=pd.DataFrame(rows)
print("\n"+"="*84)
print("DECAY SUMMARY - top 50 DEV winners")
print("="*84)
print("  mean GROSS pt/trade   DEV %+8.3f   VAL %+8.3f   LOCKBOX %+8.3f"%(df.DEV.mean(),df.VAL.mean(),df.LOCK.mean()))
print("  median                DEV %+8.3f   VAL %+8.3f   LOCKBOX %+8.3f"%(df.DEV.median(),df.VAL.median(),df.LOCK.median()))
print("  retained sign on VAL:      %d of %d"%((np.sign(df.VAL)==np.sign(df.DEV)).sum(),len(df)))
print("  retained sign on LOCKBOX:  %d of %d"%((np.sign(df.LOCK)==np.sign(df.DEV)).sum(),len(df)))
print("  VAL |t| >= 2:              %d of %d"%((df.valt.abs()>=2).sum(),len(df)))
print("\n  fraction of DEV effect retained on VAL: %.1f%%"%(100*df.VAL.mean()/df.DEV.mean()))
print("\n  NET pt/trade on VAL at several cost assumptions (mean of the 50):")
for c in (0.5,0.75,1.0,1.5):
    print("     cost %.2f pt  ->  %+7.3f   (configs positive: %d of 50)"%(c,df.VAL.mean()-c,(df.VAL-c>0).sum()))
df.to_pickle('v5/decay.pkl')
