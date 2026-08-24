#!/usr/bin/env python3
# ======================================================================
# REC-P1 - 15m stop-run reclaim, FROZEN PROSPECTIVE SPEC
# ======================================================================
# Registered by docs/BRK_PREREGISTRATION.md. This file exists to FREEZE
# the rule with a hash so that a forward evaluation months from now is
# provably the same rule, not a remembered approximation.
#
# NO BACKTEST IS RUN FROM THIS FILE. Both prior tests (PRO-OF-H3 n=476,
# MR-H3 RECLAIM n=581) spent the same 12 months of history; re-mining it
# would produce a number with no evidential value. The forward ledger is
# the only instrument that can promote this.
#
# IMPLEMENTATION NOTE - deliberately NOT wired into the NT8 host.
# Adding a candidate to V41FrozenCandidateEngine.cs would change the
# frozen engine, invalidate the cand_spec/ofh6/ofht hashes, and require
# a full parity re-verification while the prospective ledger is midway
# through forward collection. That cost is not worth paying for a
# signal-only candidate: REC-P1 is evaluated OFFLINE from the same 1m
# order-flow capture the prospective host already writes. The frozen
# engine, and OFH13_PROSPECTIVE_V1 in particular, is untouched.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import hashlib

# Lifted verbatim from analysis/v41/mrv_run.py::mr_h3 with arm='RECLAIM'
# (read from the source, not from memory) on 2026-08-23.
SPEC = {
    'name': 'REC_PROSPECTIVE_P1',
    'status': 'SIGNAL_ONLY_PROSPECTIVE_NO_ORDERS',
    'level_source': '15m swing extremes (lo_at for d=+1, hi_at for d=-1)',
    'sweep': 'bar j low < level (d=+1) or high > level (d=-1); first such level',
    'participation_gate': 'relVol >= 2.0 at bar j',
    'effort_failure_gate': None,     # this is what makes it RECLAIM, not FULL
    'reclaim_window_bars': 5,        # k in [j, j+5], consecutive bars only
    'reclaim': 'first k > j whose close is back through the swept level',
    'entry': 'close of bar k',
    'entry_gate': 'entry_ok (RTH, >= 60 min to RTH close, ATR valid)',
    'cooldown_min': 30,
    'management': 'NOT SPECIFIED - management study follows a forward pass, '
                  'it does not precede it (MRV_FINDINGS gate)',
    'prior_evidence': {
        'PRO-OF-H3': {'n': 476, 'R': 1.21, 'ff': 0.564},
        'MR-H3-RECLAIM': {'n': 581, 'mean': 7.85, 'median': 3.63, 'R': 1.23,
                          'ff': 0.547, 'signflip_p': 0.0215,
                          'day_ci': (0.00, 15.56), 'bh_q_at_M18': 0.387},
    },
    'promotion_rule': 'forward ledger only; no re-mining of spent history',
    'frozen_on': '2026-08-23',
}


def spec_hash():
    return hashlib.sha256(repr(sorted(SPEC.items())).encode()).hexdigest()[:16]


if __name__ == '__main__':
    print('REC-P1 FROZEN PROSPECTIVE SPEC')
    for k, v in SPEC.items():
        print('  %-22s %s' % (k, v))
    print('  %-22s %s' % ('spec_hash', spec_hash()))
    print('\nNo backtest is run from this file, by design.')
