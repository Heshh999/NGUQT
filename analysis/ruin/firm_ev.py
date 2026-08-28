#!/usr/bin/env python3
# Which 150K firm fits OFH13 best? Full economics, 2 MNQ contracts.
# Costs/rules looked up Aug 2026 - VERIFY before paying.
import numpy as np
R = np.load('/tmp/ofh13_rows.npy'); PV=2.0
mfe, net = R[:,0], R[:,2]
B=30000; TPD=133/108.0; CT=2

FIRMS = [
 # name, evalFee/mo, activation, target, trailDD, intraTrail, split,
 # consistencyPct, payoutCapPerCycle, cyclesPerYear
 ('Apex 150K (coupon ~$40/mo)',   40., 130., 9000., 5000., False, 1.00, 0.50, 3500., 12),
 ('Apex 150K (list $297/mo)',    297., 130., 9000., 5000., False, 1.00, 0.50, 3500., 12),
 ('Topstep 150K',                199., 149., 9000., 4500., False, 0.90, 0.40, 5000., 12),
 ('MyFundedFutures Pro 150K',    477.,   0., 9000., 4500., False, 0.80, 1.00, 99999., 26),
 ('TakeProfitTrader 150K',       360.,   0., 9000., 4500., True,  0.80, 0.50, 99999., 12),
]

def sim(target, trail, intra, seed, days=400):
    rng=np.random.default_rng(seed)
    eq=np.zeros(B); peak=np.zeros(B); live=np.ones(B,bool)
    passed=np.zeros(B,bool); pd_=np.full(B,-1); bestday=np.zeros(B)
    for day in range(days):
        k=rng.poisson(TPD,B); mx=max(1,k.max())
        idx=rng.integers(0,len(net),size=(B,mx)); dpl=np.zeros(B)
        for j in range(mx):
            act=live&(j<k)
            tn=net[idx[:,j]]*PV*CT; tm=mfe[idx[:,j]]*PV*CT
            if intra: peak=np.where(act,np.maximum(peak,eq+tm),peak)
            eq=np.where(act,eq+tn,eq); dpl=np.where(act,dpl+tn,dpl)
            if not intra: peak=np.where(act,np.maximum(peak,eq),peak)
            live&=~(live&((peak-eq)>=trail))
        bestday=np.maximum(bestday,dpl)
        p=live&(eq>=target); passed|=p
        pd_=np.where(p&(pd_<0),day+1,pd_); live&=~p
    return passed, pd_, bestday

print('=' * 104)
print('FULL ECONOMICS, 2 MNQ CONTRACTS, OFH13 (in-sample distribution)')
print('=' * 104)
print('%-30s %7s %8s %9s %10s %10s %11s' %
      ('firm','pass','months','feeToPass','consBlock','yr1 net','breakeven?'))
rows=[]
for (nm, fee, act, tgt, tr, intra, split, cons, cap, cyc) in FIRMS:
    p, pd_, bd = sim(tgt, tr, intra, 4242)
    if not p.any():
        print('%-30s %7s' % (nm,'0%')); continue
    med_days = np.median(pd_[p])
    months = med_days/21.0
    fee_to_pass = fee*np.ceil(months) + act
    # consistency: does the biggest day exceed cons% of the target?
    blocked = (bd[p] > cons*tgt).mean()
    # year-1: pass, then trade remaining months of the year at ~$760/mo gross
    gross_mo = 34.52*CT*(133/12.0)
    rem = max(0.0, 12-months)
    yr1 = tgt*split + gross_mo*rem*split - fee_to_pass
    # payout cap check
    capped = 'cap $%.0f/cyc' % cap if cap < 9999 else 'no cap'
    rows.append((nm, 100*p.mean(), months, fee_to_pass, 100*blocked, yr1, capped))
    print('%-30s %6.1f%% %8.1f %9s %9.1f%% %10s %11s'
          % (nm, 100*p.mean(), months, '$%.0f'%fee_to_pass, 100*blocked,
             '$%+.0f'%yr1, capped))

print()
print('notes: months = median trading months to hit the $9,000 target at 2 MNQ')
print('       consBlock = %% of passing runs whose single best day exceeds the')
print('                   firm consistency limit (payout risk, not eval risk)')
print('       yr1 net   = split-adjusted profit minus fees, first 12 months')
