import pandas as pd, numpy as np
def build():
    b=pd.read_pickle('v5/bars.pkl')[['dt','open','high','low','close','volume','atr']].copy()
    b['d']=b.dt.dt.normalize()
    b['m']=b.dt.dt.hour*60+b.dt.dt.minute
    # RTH = 09:30..16:00 ET inclusive of the 16:00 stamp
    rth=b[(b.m>=570)&(b.m<=960)]
    days=sorted(rth.d.unique())
    print("RTH calendar dates:",len(days))
    def last_at_or_before(df,minute):
        s=df[df.m<=minute]
        return s.close.iloc[-1] if len(s) else np.nan
    rows=[]
    g={k:v for k,v in b.groupby('d')}
    for i,d in enumerate(days):
        day=g[d]
        c0929=last_at_or_before(day,569)     # last print strictly before 09:30
        c1000=last_at_or_before(day,600)
        c1530=last_at_or_before(day,930)
        c1600=last_at_or_before(day,960)
        rows.append(dict(d=d,c0929=c0929,c1000=c1000,c1530=c1530,c1600=c1600,
                         rth_bars=int(((day.m>=570)&(day.m<=960)).sum())))
    s=pd.DataFrame(rows)
    s['prev1600']=s.c1600.shift(1)
    s['overnight']=s.c0929-s.prev1600      # 16:00 prior RTH close -> 09:29 close
    s['rth']=s.c1600-s.c0929               # the RTH move itself
    s['full']=s.overnight+s.rth
    s['open30']=s.c1000-s.c0929
    s['close30']=s.c1600-s.c1530
    s['dow']=s.d.dt.dayofweek
    s['year']=s.d.dt.year
    s['ym']=s.d.dt.to_period('M')
    # turn of month: last 3 trading days of month M + first 2 of M+1
    s['rk_fwd']=s.groupby('ym').cumcount()                    # 0 = first trading day
    s['rk_bwd']=s.groupby('ym')['d'].transform('size')-1-s.rk_fwd
    s['tom']=(s.rk_bwd<=2)|(s.rk_fwd<=1)
    def split(d):
        if d<pd.Timestamp('2023-01-01'): return 'DEV'
        if d<pd.Timestamp('2025-01-01'): return 'VAL'
        return 'LOCKBOX'
    s['split']=s.d.map(split)
    return s
if __name__=='__main__':
    s=build(); s.to_pickle('v5/sess.pkl')
    print(s[['d','overnight','rth','open30','close30','rth_bars','split']].head(3).to_string())
    print("\nrows",len(s),"  usable (prev close present):",s.overnight.notna().sum())
    print("rth_bars: median",s.rth_bars.median()," min",s.rth_bars.min()," <300:",int((s.rth_bars<300).sum()))
    print("\nsplit counts:",s.split.value_counts().to_dict())
    print("dow counts:",s.dow.value_counts().sort_index().to_dict())
    print("turn-of-month days:",int(s.tom.sum()),"of",len(s))
