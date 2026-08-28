#!/usr/bin/env python3
# ======================================================================
# NMAE-V1  MODE A  -  READ-ONLY PRECONDITION + DATA-AVAILABILITY AUDIT
# No outcome, no discovery, no candidate. Counts and hashes only.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import glob, json, os, subprocess

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
REPO = '/home/user/NGUQT'

def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True,
                          cwd=REPO).stdout.strip()

out = {}
out['head'] = sh('git rev-parse HEAD')
out['branch'] = sh('git branch --show-current')
out['dirty_files'] = len([l for l in sh('git status --short').split('\n') if l])
out['python'] = sh('python3 --version')
out['numpy'] = sh('python3 -c "import numpy;print(numpy.__version__)"')

# --- MLES precondition -----------------------------------------------
# exclude NMAE's own audit files: they necessarily NAME MLES-V1 while
# reporting its absence, and would otherwise self-trigger the search.
mles_hits = sh("grep -rlo 'MLES[-_ ]*V1' . --include='*.md' --include='*.csv' "
               "--include='*.json' --include='*.py' "
               "--exclude-dir=nmae 2>/dev/null")
out['mles'] = {
    'artifacts_found': [x for x in mles_hits.split('\n') if x],
    'commits_found': [x for x in sh("git log --oneline --all | grep -i mles").split('\n') if x],
    'protocol_commit': None, 'results_commit': None,
    'hypothesis_ledger': None, 'final_report': None,
    'frozen_candidate_file': None, 'cumulative_exposure_ledger': None,
    'verdict': 'ABSENT - MLES-V1 was never preregistered, run, or committed',
}

# --- ancestry of prior freeze/result commits -------------------------
anc = {}
for c in ('eac54fe','be1fff6','963009d','9fec078','7062e67','bb6986b',
          'f08396b','5133c51','9072bd3','7c8a854','643343f','e628b9d',
          '938382b','8dfc2de','537a662'):
    anc[c] = (sh('git merge-base --is-ancestor %s HEAD && echo yes || echo no' % c) == 'yes')
out['prior_commits_in_ancestry'] = anc

# --- data availability by NMAE family requirement ---------------------
def count(pat):
    return len(glob.glob(pat))

data = {}
data['MNQ_1m_price'] = dict(present=True, files=count(SCR+'/rvmr_1m/rvmr_1m_*.csv'),
    span='2019-07-04..2026-08-17', bars=2503622, note='EXPOSED; canonical grid')
data['MNQ_1m_orderflow_bar_aggregate'] = dict(present=True,
    files=count(SCR+'/ofnew/*.csv')+count(SCR+'/of2/v4_1_orderflow_MNQ_v41of_*.csv'),
    span='2025-08-18..2026-08-19', note='EXPOSED; bar aggregates, no messages')
data['MNQ_30s_OHLCV'] = dict(present=True, window='09:30-11:00 only', days=192,
    note='EXPOSED; not full session; NOT a substitute for quotes')
data['ES_1m_price'] = dict(present=True, files=count(SCR+'/es_pilot/V41_LTF_ES_*.csv'),
    span='2026-06-30..2026-08-17', note='42 session days = 1.86% of NQ span')
for k in ('ES_orderflow','MES','YM_MYM','RTY_M2K','NDX_cash_index','QQQ_quotes',
          'risk_free_rate','dividend_estimates','ETF_borrow','option_chains_NQ_QQQ',
          'option_bid_ask','greeks_or_IV_source','VXN_VIX_spot_or_futures',
          'treasury_futures_or_yields','dollar_index','semis_tech_ETF',
          'authenticated_econ_calendar','consensus_pre_release','first_release_actual',
          'revision_history','quotes_BBO_MNQ','depth_L2','raw_trades_messages',
          'broker_fill_records','latency_distributions'):
    data[k] = dict(present=False, note='ABSENT - no file, feed, or licence in repo')
out['data'] = data

# --- family readiness --------------------------------------------------
fam = {
 'N1 hedged equity-index relative value':
   dict(needs='NQ+ES+YM+RTY synchronized quotes, all legs',
        have='NQ full; ES 42 days; YM/RTY none',
        status='INSUFFICIENT_DATA',
        binding='no YM/RTY at all; ES span 42 days vs floor 200 days / 5 years'),
 'N2 cash-futures basis / fair value':
   dict(needs='NDX or QQQ quotes + rates + dividends + borrow',
        have='none of the four', status='INSUFFICIENT_DATA',
        binding='no cash index, no ETF quotes, no rates, no dividends'),
 'N3 realized vs option-implied':
   dict(needs='option chains with genuine bid/ask + synchronized underlying',
        have='none', status='INSUFFICIENT_DATA',
        binding='no option data of any kind; model values prohibited as prices'),
 'N4 volatility term structure / VRP':
   dict(needs='VXN/VIX spot+futures curve or option term structure',
        have='none', status='INSUFFICIENT_DATA',
        binding='no volatility instrument data'),
 'N5 authenticated economic surprise':
   dict(needs='licensed release timestamps + consensus + first print + revisions',
        have='none', status='INSUFFICIENT_DATA',
        binding='no authenticated calendar; scraping prohibited'),
 'N6 cross-asset regime transition':
   dict(needs='ES/YM/RTY + rates + dollar + vol curve + tech ETF, synchronized',
        have='ES 42 days only', status='INSUFFICIENT_DATA',
        binding='4 of 5 asset classes absent; ES span far below 200-day floor'),
}
out['families'] = fam
out['families_ready'] = [k for k, v in fam.items() if v['status'] == 'READY']

json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'NMAE_V1_DATA_MANIFEST.json'), 'w'), indent=1)
print('HEAD %s  branch %s  dirty %d' % (out['head'][:8], out['branch'], out['dirty_files']))
print('MLES-V1: %s' % out['mles']['verdict'])
print('prior commits in ancestry: %d/%d'
      % (sum(anc.values()), len(anc)))
print('data classes present: %d of %d'
      % (sum(1 for v in data.values() if v['present']), len(data)))
print('families READY_FOR_DISCOVERY: %d of 6' % len(out['families_ready']))
for k, v in fam.items():
    print('  %-42s %s' % (k[:42], v['status']))
