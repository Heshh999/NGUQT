import pandas as pd, numpy as np, pickle, time, sys
RNG=np.random.default_rng(11)
b=pd.read_pickle('v5/feat.pkl')
obs=pd.to_numeric(b.barsObserved,errors='coerce').to_numpy(float)
dev=(obs>=80)&(b.dt<'2023-01-01').to_numpy()
names,cbs,idxs,HOR=pickle.load(open('v5/qual.pkl','rb'))
Y=np.vstack([pd.to_numeric(b['net_%d'%k],errors='coerce').to_numpy(float)[dev] for k in HOR])
day=b.exday.to_numpy()[dev]
_,dayidx=np.unique(day,return_inverse=True)
n=Y.shape[1]
print("qualifying conjunctions",len(idxs),"  DEV rows",n)
def best_of(Yv):
    bb=-1e9
    for idx in idxs:
        mu=Yv[:,idx].mean(axis=1)
        v=np.abs(mu).max()          # best over horizon AND direction
        if v>bb: bb=v
    return bb
real=best_of(Y); print("REAL best |gross| = %.4f"%real)
B=20; nulls=[]
t0=time.time()
for r in range(B):
    perm=np.lexsort((RNG.random(n),dayidx))     # shuffle WITHIN day, keep day membership
    v=best_of(Y[:,perm]); nulls.append(v)
    print("  perm %2d/%d  best %8.4f   (%.0fs)"%(r+1,B,v,time.time()-t0),flush=True)
nulls=np.array(nulls)
print("\n"+"="*72)
print("PERMUTATION NULL - best conjunction found in SHUFFLED outcomes")
print("="*72)
print("  real best              %8.4f pt"%real)
print("  shuffled best: mean    %8.4f   min %8.4f   max %8.4f"%(nulls.mean(),nulls.min(),nulls.max()))
print("  permutations >= real:  %d of %d   -> p = %.3f"%((nulls>=real).sum(),B,((nulls>=real).sum()+1)/(B+1)))
np.save('v5/nulls.npy',nulls)
