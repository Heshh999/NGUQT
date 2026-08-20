import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
b=pd.read_pickle('v5/bars.pkl').reset_index(drop=True)
N=len(b); KMAX=80
c=b.close.to_numpy(float); h=b.high.to_numpy(float); l=b.low.to_numpy(float)
R=pd.to_numeric(b.stopMicroSwingLong,errors='coerce').to_numpy(float)
atr=pd.to_numeric(b.atr,errors='coerce').to_numpy(float)
day=(b.dt-pd.Timedelta(hours=18)).dt.normalize().to_numpy()
obs=pd.to_numeric(b.barsObserved,errors='coerce').to_numpy(float)
# PRE-DECLARED validity filter: R >= 1.0pt (4 ticks) and R <= 10*ATR ; full forward window
ok=np.isfinite(R)&(R>=1.0)&(R<=10*atr)&(obs>=KMAX)
print("bars %d -> valid after declared filter %d (%.2f%%)"%(N,ok.sum(),100*ok.mean()))
print("  dropped: R<1pt %d,  R>10*ATR %d,  truncated window %d"%(
    int((R<1.0).sum()),int((R>10*atr).sum()),int((obs<KMAX).sum())))

def race(M,K,pessimistic=True):
    """long from close[t]; stop close-R ; target close+M*R ; timeout exit at close[t+K].
       pessimistic=True -> if a single bar spans both levels, assume the STOP filled first."""
    idx=np.arange(N)
    stop=c-R; tgt=c+M*R
    res=np.full(N,np.nan); done=np.zeros(N,bool)
    for k in range(1,K+1):
        j=idx+k
        v=(~done)&(j<N)
        if not v.any(): break
        jj=np.where(v,j,0)
        hitS=v&(l[jj]<=stop); hitT=v&(h[jj]>=tgt)
        both=hitS&hitT
        if pessimistic: win=hitT&~hitS
        else:           win=hitT
        loss=hitS&(~win)
        res[win]=M*R[win]; res[loss]=-R[loss]
        done|=(win|loss)
    tail=(~done)
    jt=np.minimum(idx+K,N-1)
    res[tail]=c[jt[tail]]-c[tail]
    return res,done

print("\n"+"="*104)
print("P2  PATH & EXIT GEOMETRY - PRE-DECLARED CONTROLS (predicted outcome: the null)")
print("="*104)
# C1 : P(+1R before -1R)
for lab,pes in (("stop-first (pessimistic)",True),("target-first (optimistic)",False)):
    r,done=race(1.0,KMAX,pes)
    m=ok&done
    wins=(r[m]>0)
    p=wins.mean()
    se=np.sqrt(p*(1-p)/m.sum())
    print("  C1  P(+1R before -1R)  %-26s = %.4f   (n=%d, resolved %.1f%%, +-%.4f)  dev from 0.5: %+.4f"%(
        lab,p,m.sum(),100*m.sum()/ok.sum(),1.96*se,p-0.5))

# C3 : unclamped MFE vs MAE
print()
for K in (20,80):
    sh=pd.Series(h); sl=pd.Series(l)
    fmax=sh.iloc[::-1].rolling(K,min_periods=K).max().iloc[::-1].shift(-1).to_numpy(float)
    fmin=sl.iloc[::-1].rolling(K,min_periods=K).min().iloc[::-1].shift(-1).to_numpy(float)
    mfe=fmax-c; mae=c-fmin      # UNCLAMPED, rebuilt from raw OHLC
    m=ok&np.isfinite(mfe)&np.isfinite(mae)
    mu,se,t,n,kk=boot_day(mfe[m]-mae[m],day[m])
    print("  C3  K=%2d  E[MFE] %8.4f   E[MAE] %8.4f   difference %+8.4f  t %+6.2f  (drift over window %+.4f)"%(
        K,mfe[m].mean(),mae[m].mean(),mu,t,np.nanmean(c[np.minimum(np.arange(N)+K,N-1)][m]-c[m])))

# C2 : grid of target multiples ; C4 : holding cap
print("\n  C2/C4  exit grid - net is after the 1.5pt assumed round turn")
print("  %-6s %-5s %10s %10s %8s %10s %8s"%("target","K","gross pt","net pt","t(net)","net R","win%"))
rows=[]
for K in (10,20,40,80):
    for M in (0.5,1.0,1.5,2.0,3.0,5.0):
        r,done=race(M,K,True)
        m=ok&np.isfinite(r)
        g=r[m]; net=g-1.5
        mu,se,t,n,kk=boot_day(net,day[m])
        netR=np.nanmean(net/R[m])
        wr=100*(g>0).mean()
        rows.append((M,K,g.mean(),mu,t,netR,wr))
        print("  %-6.1f %-5d %10.4f %10.4f %8.2f %10.4f %8.2f"%(M,K,g.mean(),mu,t,netR,wr))
rw=pd.DataFrame(rows,columns=['M','K','gross','net','t','netR','win'])
print("\n  configurations with POSITIVE net points: %d of %d"%((rw.net>0).sum(),len(rw)))
print("  configurations with POSITIVE gross points: %d of %d"%((rw.gross>0).sum(),len(rw)))
print("  best net: M=%.1f K=%d -> %+.4f pt"%(rw.loc[rw.net.idxmax()].M,rw.loc[rw.net.idxmax()].K,rw.net.max()))
print("\n  C4 monotonicity in K (M=1.0):")
print(rw[rw.M==1.0][['K','gross','net','t']].to_string(index=False))
rw.to_pickle('v5/p2_grid.pkl')
