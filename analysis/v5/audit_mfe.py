import pandas as pd, numpy as np
b=pd.read_pickle('v5/bars.pkl')
c=b.close.to_numpy(float); h=b.high.to_numpy(float); l=b.low.to_numpy(float)
for K in (3,20,80):
    mfe=pd.to_numeric(b['mfeLong_%d'%K],errors='coerce').to_numpy(float)
    mae=pd.to_numeric(b['maeLong_%d'%K],errors='coerce').to_numpy(float)
    sh=pd.Series(h); sl=pd.Series(l)
    fmax=sh.iloc[::-1].rolling(K,min_periods=K).max().iloc[::-1].shift(-1).to_numpy(float)
    fmin=sl.iloc[::-1].rolling(K,min_periods=K).min().iloc[::-1].shift(-1).to_numpy(float)
    raw_mfe=fmax-c; raw_mae=c-fmin
    cl_mfe=np.maximum(raw_mfe,0.0); cl_mae=np.maximum(raw_mae,0.0)
    m=np.isfinite(mfe)&np.isfinite(cl_mfe)
    print("== K=%d =="%K)
    print("   MFE clamped max(0,.) exact %.4f%%"%(np.mean(np.abs(mfe[m]-cl_mfe[m])<1e-6)*100))
    print("   MAE clamped max(0,.) exact %.4f%%"%(np.mean(np.abs(mae[m]-cl_mae[m])<1e-6)*100))
    # how often does the raw version go negative? that is the clamp population
    print("   raw MFE<0 %.3f%%   raw MAE<0 %.3f%%"%((raw_mfe[m]<0).mean()*100,(raw_mae[m]<0).mean()*100))
    bad=m&(np.abs(mfe-cl_mfe)>=1e-6)
    if bad.sum():
        i=np.where(bad)[0][:3]
        print("   residual mismatches:",int(bad.sum()))
        for j in i:
            print("     t=%s file_mfe=%.2f recon=%.2f close=%.2f fmax=%.2f"%(b.dt.iloc[j],mfe[j],cl_mfe[j],c[j],fmax[j]))
