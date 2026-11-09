#!/usr/bin/env python3
# MROF-YT-PSYCHECK-1.0 suite. Synthetic recorder-format Monday sessions
# (mles_v12_synth), one in New York summer time and one in winter time,
# with highs and lows planted in hours that only some windows contain;
# the check must give each window's own extremes, read only DEV or
# EXPOSED sessions, leave flagged trades out and name the matching
# window. Synthetic prices verify CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists.
import csv
import datetime as dt
import gc
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_adapter as AD        # noqa: E402
import mles_v12_synth as SY          # noqa: E402
import mrofyt_psycheck as PC         # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def utc(*a):
    return (dt.datetime(*a, tzinfo=dt.timezone.utc)
            - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)).total_seconds()


WORK = tempfile.mkdtemp(prefix='mrofyt_psy_')

# ---------------------------------------------------------------------
# PC1: the three windows, summer and winter
# ---------------------------------------------------------------------
s, w = PC.windows('20260914'), PC.windows('20261102')
t('PC1: Monday 14 Sep (New York summer time) and Monday 2 Nov (winter, the '
  'Sunday the clocks went back): TR_CLOCK Monday 00:00-08:00 GMT, TR_4H the '
  '22:00 and 02:00 New York 4-hour candles, FIRST_8H 18:00-02:00 New York',
  s['TR_CLOCK'] == (utc(2026, 9, 14), utc(2026, 9, 14, 8)) and
  s['TR_4H'] == (utc(2026, 9, 14, 2), utc(2026, 9, 14, 10)) and
  s['FIRST_8H'] == (utc(2026, 9, 13, 22), utc(2026, 9, 14, 6)) and
  w['TR_CLOCK'] == (utc(2026, 11, 2), utc(2026, 11, 2, 8)) and
  w['TR_4H'] == (utc(2026, 11, 2, 3), utc(2026, 11, 2, 11)) and
  w['FIRST_8H'] == (utc(2026, 11, 1, 23), utc(2026, 11, 2, 7)) and
  PC.ny_clock(w['TR_CLOCK'][0]) == 'Sun 19:00' and
  PC.ny_clock(s['TR_CLOCK'][0]) == 'Sun 20:00' and
  PC.ny_clock(w['TR_4H'][1]) == 'Mon 06:00')


# ---------------------------------------------------------------------
# synthetic Monday sessions with planted extremes
# ---------------------------------------------------------------------
def planted(open_utc):
    """Price path, one step a second from the Sunday 18:00 open: a high
    at 18:30 (FIRST_8H only), a low at 20:30 (FIRST_8H and TR_CLOCK), a
    high at 03:00 (TR_CLOCK and TR_4H, in summer), a low at 05:00
    (TR_4H only), New York time in summer."""
    marks = {1800: 100.0, 9000: -80.0, 32400: 60.0, 39600: -120.0}

    def p(i):
        for at, dv in marks.items():
            if at <= i < at + 60:
                return 15000.0 + dv
        return 15000.0 + (i % 40) * 0.25 / 4
    return p


D = os.path.join(WORK, 'cap')
SUMMER_OPEN = utc(2026, 9, 13, 22)          # Sunday 18:00 New York (EDT)
WINTER_OPEN = utc(2026, 11, 1, 23)          # Sunday 18:00 New York (EST)
for ses, t0, cid in (('20260914', SUMMER_OPEN, 'psyS'),
                     ('20261102', WINTER_OPEN, 'psyW')):
    SY.synth_run(D, n_depth=50400, dt_step=1.0, t0=t0,
                 price_path=planted(t0), trade_every=10, quote_every=5,
                 cid=cid, session=ses, seed=3)
gc.collect()     # mles_v12_synth leaves its manifests to the collector


def trades_of(ses):
    out = []
    for f in sorted(os.listdir(D)):
        if f.endswith('_trades.csv') and '_%s_' % ses in f:
            with open(os.path.join(D, f), newline='') as fh:
                for r in csv.DictReader(fh):
                    out.append((AD.iso_to_epoch(r['tExchUtc']),
                                float(r['px'])))
    return out


def by_hand(ses, name):
    a, b = PC.windows(ses)[name]
    px = [p for tt, p in trades_of(ses) if a <= tt < b]
    return max(px), min(px), len(px)


rep = PC.run(D, ledger=os.path.join(WORK, 'none.json'))
wk = {w_['week']: w_ for w_ in rep['weeks']}
sv = wk['20260914']['windows']
hand = {k: by_hand('20260914', k) for k in PC.WINDOWS}
t('PC2: in summer each window gives its own extremes, as counted by hand '
  'from the trades file: FIRST_8H the 18:30 high and 20:30 low, TR_CLOCK '
  'the 03:00 high and 20:30 low, TR_4H the 03:00 high and 05:00 low; all '
  'three differ and are complete',
  all((sv[k]['hi'], sv[k]['lo'], sv[k]['n']) == hand[k] for k in PC.WINDOWS)
  and sv['FIRST_8H']['hi'] > 15090 and sv['FIRST_8H']['lo'] < 14930 and
  15050 < sv['TR_CLOCK']['hi'] < 15070 and sv['TR_CLOCK']['lo'] < 14930 and
  15050 < sv['TR_4H']['hi'] < 15070 and sv['TR_4H']['lo'] < 14890 and
  len({(sv[k]['hi'], sv[k]['lo']) for k in PC.WINDOWS}) == 3 and
  all(sv[k]['status'] == 'COMPLETE' for k in PC.WINDOWS))

# ---------------------------------------------------------------------
# PC3: the gate
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'exposed.json')
with open(led, 'w') as fh:
    json.dump(dict(exposed_days=[dict(session='20261102',
                                      label='EXPOSED_PILOT_DEV')]), fh)
raw_led = open(led).read()
rep2 = PC.run(D, ledger=led)
wk2 = {w_['week']: w_ for w_ in rep2['weeks']}
wv = wk2['20261102']['windows']
t('PC3: a held-out Monday is listed and never read; once the exposure '
  'ledger marks it EXPOSED it is read, in winter time (TR_CLOCK 19:00-03:00 '
  'New York); the ledger is left untouched',
  rep['held_out_not_read'] == ['20261102'] and '20261102' not in wk and
  rep2['held_out_not_read'] == [] and
  wv['TR_CLOCK']['window_ny'] == 'Sun 19:00 - Mon 03:00 New York' and
  all((wv[k]['hi'], wv[k]['lo'], wv[k]['n']) == by_hand('20261102', k)
      for k in PC.WINDOWS) and open(led).read() == raw_led)

# ---------------------------------------------------------------------
# PC4: matching the chart
# ---------------------------------------------------------------------
c = sv['TR_CLOCK']
rep3 = PC.run(D, expect={'20260914': (c['hi'], c['lo'])}, ledger=led)
w3 = {w_['week']: w_ for w_ in rep3['weeks']}['20260914']['windows']
rep4 = PC.run(D, expect={'20260914': (c['hi'] + 0.25, c['lo']),
                         '20260921': (1.0, 0.0)}, ledger=led)
txt3, txt4 = PC.text(rep3), PC.text(rep4)
t('PC4: the chart\'s numbers name the window that gives them exactly; a '
  'quarter point off is no match, shown as the difference; a week not '
  'recorded is said so',
  w3['TR_CLOCK']['exact'] and not w3['TR_4H']['exact'] and
  not w3['FIRST_8H']['exact'] and
  rep3['verdict']['matching_window'] == 'TR_CLOCK' and
  'MATCH: TR_CLOCK gives your chart' in txt3 and
  rep4['verdict']['matching_window'] is None and
  'Hi -0.25 Lo +0.00' in txt4 and 'NO WINDOW MATCHES EXACTLY' in txt4 and
  'week of Monday 20260921: not in the recordings' in txt4)

# ---------------------------------------------------------------------
# PC5: data quality
# ---------------------------------------------------------------------
tf = [f for f in os.listdir(D) if f.endswith('_trades.csv') and
      '_20260914_' in f][0]
p = os.path.join(D, tf)
with open(p, newline='') as fh:
    rows = list(csv.reader(fh))
head = rows[0]
i_ex, i_px, i_fl = (head.index('tExchUtc'), head.index('px'),
                    head.index('flags'))
for r in rows[1:]:
    tt = AD.iso_to_epoch(r[i_ex])
    if utc(2026, 9, 14, 1) <= tt < utc(2026, 9, 14, 1, 0, 30):
        r[i_px], r[i_fl] = '99999.00', 'DATA_SUPPRESSED'
kept = [r for r in rows[1:]
        if not utc(2026, 9, 14, 7) <= AD.iso_to_epoch(r[i_ex])
        < utc(2026, 9, 14, 7, 20)]          # 03:00-03:20 New York
with open(p, 'w', newline='') as fh:
    csv.writer(fh, lineterminator='\n').writerows([head] + kept)
rep5 = PC.run(D, ledger=led)
w5 = {w_['week']: w_ for w_ in rep5['weeks']}['20260914']
t('PC5: trades the recorder flagged are left out and counted (a 99,999 '
  'print never becomes Psy-Hi); a 20-minute hole at 03:00 New York marks '
  'the two windows it falls in INCOMPLETE, with the reason, and not '
  'FIRST_8H, which closed at 02:00',
  w5['suppressed_trades'] == 3 and
  all(w5['windows'][k]['hi'] < 20000 for k in PC.WINDOWS) and
  w5['windows']['TR_CLOCK']['status'] == 'INCOMPLETE' and
  w5['windows']['TR_4H']['status'] == 'INCOMPLETE' and
  'a 20-minute hole in the trades' in
  '; '.join(w5['windows']['TR_CLOCK']['why']) and
  w5['windows']['FIRST_8H']['status'] == 'COMPLETE')

# ---------------------------------------------------------------------
# PC6: the command
# ---------------------------------------------------------------------
out = os.path.join(WORK, 'psy.json')
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = PC.main([])
    rc1 = PC.main([D, '--expect', '20260914:%.2f:%.2f' % (c['hi'], c['lo']),
                   '--out', out])
    rc2 = PC.main([D, '--expect', '20260914:bad'])
    rc3 = PC.main([D, '--frob'])
with open(out) as fh:
    jo = json.load(fh)
t('PC6: the command prints its use without a folder, writes the report, '
  'refuses a malformed --expect or an unknown argument, and says it reads '
  'trades only',
  rc0 == 2 and rc1 == 0 and rc2 == 2 and rc3 == 2 and
  jo['psycheck'] == PC.PSYCHECK_VERSION and
  'Reads trades only' in buf.getvalue() and
  '--expect takes WEEK:HI:LO' in buf.getvalue())

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
