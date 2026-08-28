#!/usr/bin/env python3
# How much of the "99% pass" is the EDGE, and how much is the RULES?
# Apex 150K: target $9,000, trailing DD $5,000 EOD, 2 MNQ contracts.
import numpy as np
R=np.load('/tmp/ofh13_rows.npy'); PV=2.0
mfe,net=R[:,0],R[:,2]
B=40000; TPD=133/108.; CT=2; TGT=9000.; TR=5000.
mu=net.mean(); centered=net-mu

def sim(edge_frac, seed, days=400):
    """edge_frac 1.0 = history repeats. 0.0 = no edge at all,
    identical trade shape/vol. Losses unchanged in shape."""
    rng=np.random.default_rng(seed)
    eq=np.zeros(B); peak=np.zeros(B); live=np.ones(B,bool)
    passed=np.zeros(B,bool); pd_=np.full(B,-1)
    for day in range(days):
        k=rng.poisson(TPD,B); mx=max(1,k.max())
        idx=rng.integers(0,len(net),size=(B,mx))
        for j in range(mx):
            act=live&(j<k)
            tn=(centered[idx[:,j]]+mu*edge_frac)*PV*CT
            tm=mfe[idx[:,j]]*PV*CT
            eq=np.where(act,eq+tn,eq)
            peak=np.where(act,np.maximum(peak,eq),peak)
            live&=~(live&((peak-eq)>=TR))
        p=live&(eq>=TGT); passed|=p
        pd_=np.where(p&(pd_<0),day+1,pd_); live&=~p
    return passed, pd_, live

print('=' * 78)
print('APEX 150K EVAL, 2 MNQ, EOD trailing $5,000, target $9,000')
print('question: how much of the pass rate survives if the edge does not?')
print('=' * 78)
print('%-34s %8s %8s %9s %9s' % ('true forward edge','pass','blow','timeout','medDays'))
for frac,lab in ((1.00,'100% of history (in-sample)'),
                 (0.75,'75% of history'),
                 (0.50,'50% of history'),
                 (0.25,'25% of history'),
                 (0.00,'ZERO edge, same trade shape')):
    p,pd_,live=sim(frac, 31337)
    timeout=live.mean()          # still alive but never reached target
    blow=1-p.mean()-timeout
    print('%-34s %7.1f%% %7.1f%% %8.1f%% %9s'
          % (lab, 100*p.mean(), 100*blow, 100*timeout,
             ('%.0f'%np.median(pd_[p])) if p.any() else 'n/a'))

print()
print('mean per trade at each level (2 MNQ, after costs):')
for frac in (1.0,0.75,0.5,0.25,0.0):
    print('   %3.0f%% edge -> $%+.2f/trade' % (100*frac, mu*frac*PV*CT))
