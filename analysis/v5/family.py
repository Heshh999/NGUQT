import pandas as pd, numpy as np, sys
sys.path.insert(0,'v5'); from est import *
s=pd.read_pickle('v5/sess.pkl'); s=s[s.overnight.notna()].copy()
d=pd.read_pickle('V4LAB/flow.pkl').copy()
d['dt']=pd.to_datetime(d.date.astype(str)+' '+d.timeEt.astype(str)); d=d.sort_values('dt').reset_index(drop=True)
c=d.close.to_numpy(float); K=20
d['net_20']=np.r_[c[K:]-c[:-K],np.full(K,np.nan)]
ex=(d.dt-pd.Timedelta(hours=18)).dt.normalize(); d['exday']=ex
same=np.r_[(ex.values[K:]==ex.values[:-K]),np.zeros(K,bool)]; d.loc[~same,'net_20']=np.nan
d['imb']=d.buyImbalanceCount-d.sellImbalanceCount

F=[]
def add(hid,desc,pred,eff,t,note=""):
    F.append(dict(id=hid,desc=desc,pred=pred,eff=eff,t=t,p=two_sided_p(t),note=note))
# --- P1
_,_,t1a,_=boot_mean(s.overnight); _,_,t1b,_=boot_mean(s.overnight-s.rth)
e1a=s.overnight.mean(); e1b=(s.overnight-s.rth).mean()
# conjunction -> intersection-union test: p = max of component p's
p1=max(two_sided_p(t1a),two_sided_p(t1b))
F.append(dict(id='H1',desc='overnight >0 AND > RTH (conjunction)',pred='+',eff=e1b,t=t1b,p=p1,
              note='component a: %+.2f t=%.2f ; component b BINDS'%(e1a,t1a)))
e,se,t,n=boot_mean(s.rth);                        add('H2','RTH mean <= 0','-',e,t)
e,se,t,n=boot_diff(s[s.tom].full,s[~s.tom].full); add('H3','turn-of-month minus rest','+',e,t)
e,se,t,n=boot_corr(s.overnight.values,s.open30.values); add('H4','corr(overnight, 09:30-10:00)','-',e,t)
e,se,t,n=boot_mean(s.close30);                    add('H5','15:30-16:00 mean','+',e,t)
e,se,t,n=boot_diff(s[s.dow==0].rth,s[s.dow!=0].rth); add('H6','Monday RTH minus other RTH','-',e,t)
# --- P3
q9=d.barDelta.quantile(.90); e,se,t,n,k=boot_day(d.loc[d.barDelta>=q9,'net_20'],d.loc[d.barDelta>=q9,'exday']); add('H7','top-decile barDelta','+',e,t)
m8=(d.newHigh20==True)&(d.cumDeltaChange20<0);   e,se,t,n,k=boot_day(d.loc[m8,'net_20'],d.loc[m8,'exday']); add('H8','20-bar high on negative cum-delta','-',e,t)
hi=d.imb>=d.imb.quantile(.90); lo=d.imb<=d.imb.quantile(.10)
a=boot_day(d.loc[hi,'net_20'],d.loc[hi,'exday']); bq=boot_day(d.loc[lo,'net_20'],d.loc[lo,'exday'])
se=np.sqrt(a[1]**2+bq[1]**2); e=a[0]-bq[0];      add('H9','imbalance top-decile minus bottom','+',e,e/se)
qp=d.pocdisp if 'pocdisp' in d else (d.close-d.pocPrice)
m10=qp>=qp.quantile(.90);                        e,se,t,n,k=boot_day(d.loc[m10,'net_20'],d.loc[m10,'exday']); add('H10','close far above POC','-',e,t)

f=pd.DataFrame(F)
f['dir_ok']=[(np.sign(r.eff)>0)==(r.pred=='+') for r in f.itertuples()]
rej,crit=bh(f.p.values,q=0.05)
f['bh_crit']=crit; f['bh_sig']=rej
f=f.sort_values('p')
print("="*112)
print("V5 CONFIRMATORY FAMILY - ALL 10 HYPOTHESES, COMPLETE, BH q=0.05")
print("="*112)
print("%-4s %-38s %5s %10s %8s %9s %9s %7s %7s"%("id","hypothesis","pred","effect","t","p","BH crit","BH sig","dir OK"))
for r in f.itertuples():
    print("%-4s %-38s %5s %10.4f %8.2f %9.5f %9.5f %7s %7s"%(
        r.id,r.desc[:38],r.pred,r.eff,r.t,r.p,r.bh_crit,"YES" if r.bh_sig else "no","YES" if r.dir_ok else "NO"))
print("\nBH-significant: %d of 10.   BH-significant AND in predicted direction: %d of 10."%(
    f.bh_sig.sum(),(f.bh_sig&f.dir_ok).sum()))
for r in f.itertuples():
    if r.note: print("   note %s: %s"%(r.id,r.note))
f.to_pickle('v5/family.pkl')
