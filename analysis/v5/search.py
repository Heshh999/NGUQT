import pandas as pd, numpy as np, itertools, sys, time
sys.path.insert(0,'v5'); from preds import build
RNG=np.random.default_rng(7)
b=pd.read_pickle('v5/feat.pkl')
obs=pd.to_numeric(b.barsObserved,errors='coerce').to_numpy(float)
base=(obs>=80)
dev=base&(b.dt<'2023-01-01').to_numpy()
print("DEV bars",dev.sum())
P=build(b,dev)
names=sorted(P); print("predicates:",len(names))
M=np.vstack([P[k][dev] for k in names])           # (npred, ndev) bool
HOR=[10,20,40,80]
Y=np.vstack([pd.to_numeric(b['net_%d'%k],errors='coerce').to_numpy(float)[dev] for k in HOR])
day=b.exday.to_numpy()[dev]
udays,dayidx=np.unique(day,return_inverse=True)
n=M.shape[1]; print("DEV rows",n,"days",len(udays))
MINN,MAXR,MINDAYS=300,0.02,60

combos=[]
for r in (2,3):
    combos+=list(itertools.combinations(range(len(names)),r))
print("conjunctions to test:",len(combos))

t0=time.time(); qual=[]
for ci,cb in enumerate(combos):
    m=M[cb[0]]
    for j in cb[1:]: m=m&M[j]
    c=int(m.sum())
    if c<MINN or c>MAXR*n: continue
    idx=np.flatnonzero(m)
    if len(np.unique(dayidx[idx]))<MINDAYS: continue
    qual.append((cb,idx))
    if ci%2000==0: print("  %d/%d  qualifying %d  %.0fs"%(ci,len(combos),len(qual),time.time()-t0),flush=True)
print("qualifying conjunctions: %d   (%.0fs)"%(len(qual),time.time()-t0))
np.save('v5/qual_meta.npy',np.array([len(qual)]))
import pickle; pickle.dump((names,[q[0] for q in qual],[q[1] for q in qual],HOR),open('v5/qual.pkl','wb'))

def score(Yv):
    """best gross mean over (horizon, direction) for every qualifying conjunction"""
    best=np.full(len(qual),-1e9); meta=[None]*len(qual)
    for i,(cb,idx) in enumerate(qual):
        yy=Yv[:,idx]
        mu=yy.mean(axis=1)
        for h in range(len(HOR)):
            for d in (1,-1):
                v=d*mu[h]
                if v>best[i]: best[i]=v; meta[i]=(HOR[h],d,len(idx))
    return best,meta
best,meta=score(Y)
o=np.argsort(-best)
print("\nREAL DATA - top 10 conjunctions by gross mean points per trade")
print("%-58s %6s %5s %7s %9s"%("conjunction","K","dir","n","gross"))
for i in o[:10]:
    cb,idx=qual[i]; K,d,nn=meta[i]
    print("%-58s %6d %5d %7d %9.4f"%(" & ".join(names[j] for j in cb),K,d,nn,best[i]))
np.save('v5/best_real.npy',best)
pickle.dump(meta,open('v5/meta_real.pkl','wb'))
