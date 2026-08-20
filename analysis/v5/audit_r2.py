import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl').reset_index(drop=True)
R=pd.to_numeric(b.stopMicroSwingLong,errors='coerce')
print("R = stopMicroSwingLong, distribution over 2.5M bars:")
for q in [0,.001,.01,.05,.25,.5,.75,.95,.99,.999,1]:
    print("   q%-6.3f  %9.2f pt"%(q,R.quantile(q)))
print("\n   R == 0        : %d bars (%.4f%%)"%((R==0).sum(),(R==0).mean()*100))
print("   R < 0.5pt(2tk): %d bars (%.4f%%)"%((R<0.5).sum(),(R<0.5).mean()*100))
print("   R > 50pt      : %d bars (%.4f%%)"%((R>50).sum(),(R>50).mean()*100))
print("   R > 200pt     : %d bars (%.4f%%)"%((R>200).sum(),(R>200).mean()*100))
atr=pd.to_numeric(b.atr,errors='coerce')
print("\n   R/ATR median %.2f   q99 %.2f   max %.1f"%((R/atr).median(),(R/atr).quantile(.99),(R/atr).max()))
