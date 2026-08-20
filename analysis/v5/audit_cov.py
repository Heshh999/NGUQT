import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl')
t=b.dt.reset_index(drop=True)
print("bars %d  span %s -> %s"%(len(b),t.min(),t.max()))
print("duplicate timestamps:",int(t.duplicated().sum()),"  monotonic:",t.is_monotonic_increasing)
gapmin=t.diff().dt.total_seconds().div(60)
prev=t.shift(1)
big=(gapmin>=5).fillna(False)
# classify each gap ONCE, in priority order
def mins(x): return x.dt.hour*60+x.dt.minute
kind=pd.Series('UNEXPLAINED',index=t.index)
kind[~big]='-'
weekend = big & (t.dt.dayofweek==6)                       # resumes Sunday
holiday_or_reopen = big & (~(t.dt.dayofweek==6)) & (mins(t)>=1080) & (mins(t)<=1110)   # 18:00-18:30 reopen
maint = big & (mins(prev)>=960) & (mins(prev)<=990) & (mins(t)>=975) & (mins(t)<=1005) # 16:00-16:45 window
kind[maint]='MAINTENANCE_1615_1630'
kind[holiday_or_reopen & (kind=='UNEXPLAINED')]='DAILY_REOPEN_1800'
kind[weekend & (kind=='UNEXPLAINED')]='WEEKEND'
vc=kind[big].value_counts()
print("\ngaps >= 5 minutes, classified once each:")
for k,v in vc.items(): print("   %-24s %6d"%(k,v))
print("\nquiet minutes (1 < gap < 5, NinjaTrader prints no bar when nothing trades):",int(((gapmin>1)&(gapmin<5)).sum()))
u=big&(kind=='UNEXPLAINED')
print("\nUNEXPLAINED gaps: %d  (%.4f%% of bar transitions)"%(int(u.sum()),u.mean()*100))
if u.sum():
    df=pd.DataFrame({'from':prev[u],'to':t[u],'min':gapmin[u]}).nlargest(10,'min')
    for _,r in df.iterrows(): print("   %s -> %s   %6.0f min"%(r['from'],r['to'],r['min']))
    print("\n   by year:",df.assign(y=df['to'].dt.year).y.value_counts().to_dict())
    allu=pd.DataFrame({'to':t[u],'min':gapmin[u]})
    print("   median unexplained gap: %.0f min ; >1 day: %d"%(allu['min'].median(),(allu['min']>1440).sum()))
print("\nbars/year:"); print(b.groupby(b.dt.dt.year).size().to_string())
print("\nsession days/year:"); print(b.groupby(b.dt.dt.year)['date'].nunique().to_string())
