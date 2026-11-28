#!/usr/bin/env python3
# MROF-YT-W34-RANGE-1.0 suite. The index file and the value a session
# may use, the range and the inputs by hand, least squares on exact
# data, the walk forward without a look ahead, a market's numbers
# against independent sums on a tape whose range follows the index, the
# calendar and the events by hand, the verdict on fabricated reports,
# and the reads and the ledger end to end on synthetic NinjaTrader-format
# exports. Synthetic data verifies CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists.
import collections
import datetime as _dt
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_dealer33 as W33        # noqa: E402
import mrofyt_markets28 as W28       # noqa: E402
import mrofyt_range34 as H           # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return a is not None and abs(a - b) <= tol


def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


def stopped(fn):
    try:
        fn()
    except CX.ContextDataError as exc:
        return str(exc)
    return None


WORK = tempfile.mkdtemp(prefix='mrofyt_w34_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, H.REGISTRATION),
                    encoding='utf-8').read().split())


def mk(session, o, pc, closes):
    c = list(closes) + [closes[-1]] * (N - len(closes))
    return S.Day(session, 'NQ 12-21', o, pc, c, list(c), list(c), [1.0] * N)


def flat(session, o, pc, marks):
    c, last = [], o
    for j in range(1, N + 1):
        last = marks.get(j, last)
        c.append(last)
    return mk(session, o, pc, c)


def weekdays(first, last):
    out, d = [], first
    while d <= last:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def ymd(d):
    return d.strftime('%Y%m%d')


EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u_ = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u_ < w[1]):
            return u_
    return local_epoch + 5 * 3600


def stamp(d, minute):
    loc = int((_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
               - EPOCH).total_seconds()) + minute * 60
    return _dt.datetime.fromtimestamp(to_utc(loc) + 60, _dt.timezone.utc
                                      ).strftime('%Y%m%d %H%M%S')


def snap(x, tick):
    return round(round(x / tick) * tick, 2)


def make_rows(first, last, seed, tick=0.25, px0=10000.0, sd=2.0):
    """[(date, row)]: every weekday from `first` to `last` has bars
    08:30-16:14 ET, a random walk on the tick that opens a little back
    toward px0 and is wilder on some days than on others; one stray bar
    on every Saturday and Sunday."""
    rng = random.Random(seed)
    px = pc = px0
    out, d = [], first
    while d <= last:
        if d.weekday() >= 5:
            out.append((d, '%s;%.2f;%.2f;%.2f;%.2f;1' % (
                stamp(d, 11 * 60), px, px, px, px)))
        else:
            px = snap(pc + 0.1 * (px0 - pc) + rng.gauss(0, 10.0 * sd), tick)
            wild = sd * rng.choice((0.6, 1.0, 1.0, 1.8))
            for m in range(8 * 60 + 30, 16 * 60 + 15):
                o = px
                px = snap(px + rng.gauss(0, wild), tick)
                h, lo = max(o, px) + tick, min(o, px) - tick
                v = 50 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                                else 900)
                out.append((d, '%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                    stamp(d, m), o, h, lo, px, v)))
                if m == 15 * 60 + 59:
                    pc = px
        d += _dt.timedelta(days=1)
    return out


def write(folder, name, rows):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(r for _d, r in rows) + '\n')
    return folder


def iv_file(name, series, values, head='observation_date'):
    p = os.path.join(WORK, name)
    with open(p, 'w') as fh:
        fh.write('%s,%s\n' % (head, series))
        for d, v in values:
            fh.write('%s,%s\n' % (d, v))
    return p


# ---------------------------------------------------------------------
# H1: the index file, and the value a session may use
# ---------------------------------------------------------------------
p1 = iv_file('vix1.csv', 'VIXCLS', [
    ('2021-01-04', '20.5'), ('2021-01-05', '.'), ('2021-01-06', '21.25'),
    ('2021-01-08', '19'), ('2021-01-15', '')])
iv1 = H.read_iv(p1, 'ES')
t('H1: the index file is FRED\'s, one value a day, a day without one '
  'left out; a session uses the last value dated before it, never its '
  'own day\'s, and none when that is more than 5 calendar days old; the '
  'file of another index stops the read',
  iv1 == [('20210104', 20.5), ('20210106', 21.25), ('20210108', 19.0)] and
  H.iv_before(iv1, '20210104') is None and
  H.iv_before(iv1, '20210105') == 20.5 and
  H.iv_before(iv1, '20210106') == 20.5 and
  H.iv_before(iv1, '20210107') == 21.25 and
  H.iv_before(iv1, '20210111') == 19.0 and
  H.iv_before(iv1, '20210113') == 19.0 and
  H.iv_before(iv1, '20210114') is None and
  'needs VXNCLS' in stopped(lambda: H.read_iv(p1, 'NQ')) and
  'needs RVXCLS' in stopped(lambda: H.read_iv(p1, 'RTY')) and
  'cannot be read' in stopped(lambda: H.read_iv(
      os.path.join(WORK, 'none.csv'), 'ES')) and
  'is not "date,value"' in stopped(lambda: H.read_iv(iv_file(
      'bad.csv', 'VIXCLS', [('2021-01-04', 'abc')]), 'ES')) and
  'holds no value' in stopped(lambda: H.read_iv(iv_file(
      'empty.csv', 'VIXCLS', [('2021-01-04', '.')]), 'ES')) and
  H.SERIES == dict(NQ='VXNCLS', ES='VIXCLS', RTY='RVXCLS') and
  H.IV_MAX_AGE == 5)

# ---------------------------------------------------------------------
# H2: the range and the inputs by hand
# ---------------------------------------------------------------------
WD2 = weekdays(D(2021, 1, 4), D(2021, 2, 5))          # 25 sessions
days2, order2 = {}, []
for i, d in enumerate(WD2):
    a, b = 0.6 * (10 + i), 0.4 * (10 + i)
    days2[ymd(d)] = flat(ymd(d), 1000.0, 1000.0,
                         {100: 1000.0 + a, 200: 1000.0 - b, 300: 1000.0})
    order2.append(ymd(d))
R2_ = [(10 + i) / 1000.0 for i in range(25)]
iv2 = [(ymd(d), 15.0 + i) for i, d in enumerate(WD2)]
tab2 = H.table(days2, order2, iv2)
r23 = tab2[23]
a22, b22 = 0.6 * 32, 0.4 * 32
dn22 = math.log((1000.0 - b22) / (1000.0 + a22)) ** 2
up22 = math.log((1000.0 + a22) / 1000.0) ** 2 + \
    math.log(1000.0 / (1000.0 - b22)) ** 2
t('H2: R is the session\'s highest high less its lowest low over the '
  'open; a session\'s inputs are the mean R of the 14 sessions before, '
  'of the one, the 5 and the 22 before, the index\'s last value before '
  'it, and the falling and rising variance of the session before; none '
  'of them holds the session itself',
  all(near(H.cash_range(days2[s]), R2_[i], 1e-12)
      for i, s in enumerate(order2)) and
  len(tab2) == 25 and tab2[0]['iv'] is None and tab2[0]['down'] is None
  and tab2[13]['atr'] is None and tab2[21]['har'] is None and
  near(tab2[14]['atr'], math.log(S.mean(R2_[0:14])), 1e-12) and
  near(r23['y'], math.log(R2_[23]), 1e-12) and
  near(r23['atr'], math.log(S.mean(R2_[9:23])), 1e-12) and
  near(r23['har'][0], math.log(R2_[22]), 1e-12) and
  near(r23['har'][1], math.log(S.mean(R2_[18:23])), 1e-12) and
  near(r23['har'][2], math.log(S.mean(R2_[1:23])), 1e-12) and
  near(r23['iv'], math.log(15.0 + 22), 1e-12) and
  near(r23['down'][0], math.log(dn22), 1e-9) and
  near(r23['down'][1], math.log(up22), 1e-9) and
  [r['session'] for r in H.usable(tab2)] == order2[22:] and
  H.semis(flat('20210104', 1000.0, 1000.0, {100: 1010.0})) is None and
  (H.ATR_N, H.HAR_N) == (14, (1, 5, 22)))

# ---------------------------------------------------------------------
# H3: least squares on exact data
# ---------------------------------------------------------------------
rng = random.Random(3)
X3 = [[1.0, rng.gauss(0, 1), rng.gauss(5, 2)] for _k in range(40)]
y3 = [1.0 + 2.0 * a - 3.0 * b for _one, a, b in X3]
b3 = H.ols(X3, y3)
xs3 = [1.0, 2.0, 3.0, 4.0]
ys3 = [2.0, 4.0, 5.0, 4.0]
b3h = H.ols([[1.0, v] for v in xs3], ys3)


def singular():
    try:
        H.ols([[1.0, 2.0, 4.0]] * 10, [1.0] * 10)
    except ValueError:
        return True
    return False


t('H3: least squares gives back 1, 2 and -3 on data built from them, '
  'and by hand a slope of 0.7 and an intercept of 2 on four points; '
  'inputs that do not determine a fit are refused',
  all(near(g, w, 1e-9) for g, w in zip(b3, (1.0, 2.0, -3.0))) and
  near(b3h[1], 0.7, 1e-12) and near(b3h[0], 2.0, 1e-12) and
  near(H.predict(b3h, [1.0, 10.0]), 9.0, 1e-12) and singular())


# ---------------------------------------------------------------------
# H4: the walk forward looks at nothing ahead
# ---------------------------------------------------------------------
def rows4(change=None):
    out = []
    for d in weekdays(D(2019, 1, 1), D(2022, 3, 31)):
        s = ymd(d)
        x = 1.0 + (d.toordinal() % 7) / 10.0 + (d.day % 5) / 7.0
        k = 2.0 if s < '20210101' else 5.0
        y = k * x
        if change and s >= change:
            y += 100.0
        out.append(dict(session=s, y=y, atr=x, har=(x, x, x), iv=x,
                        down=None))
    return out


R4 = rows4()
yrs4 = H.forecast_years([r['session'] for r in R4])
f4 = H.walk(R4, yrs4, H.MODELS['ATR'], 'ATR')
f4b = H.walk(rows4(change='20210101'), yrs4, H.MODELS['ATR'], 'ATR')
x4 = {r['session']: r['atr'] for r in R4}
b22 = H.ols([[1.0, r['atr']] for r in R4 if r['session'] < '20220101'],
            [r['y'] for r in R4 if r['session'] < '20220101'])
few = [r for r in R4 if r['session'] >= '20201110']
t('H4: the first forecast year is the third calendar year; each year is '
  'forecast from the fit on the sessions before it only: 2021 keeps the '
  'rule of 2019-2020 whatever 2021 itself does, 2022 is the fit to the '
  'end of 2021; fewer than 60 sessions before a year stop the run',
  yrs4 == ['2021', '2022'] and
  list(f4)[0] == min(s for s in x4 if s >= '20210101') and
  all(s[:4] in ('2021', '2022') for s in f4) and
  all(near(f4[s], 2.0 * x4[s], 1e-8) for s in f4 if s[:4] == '2021') and
  all(near(f4b[s], f4[s], 1e-12) for s in f4 if s[:4] == '2021') and
  all(near(f4[s], b22[0] + b22[1] * x4[s], 1e-9)
      for s in f4 if s[:4] == '2022') and
  any(abs(f4[s] - 2.0 * x4[s]) > 0.1 for s in f4 if s[:4] == '2022') and
  'at least 60 are needed' in stopped(lambda: H.walk(
      few, ['2021'], H.MODELS['ATR'], 'ATR')) and
  H.forecast_years(['20190102', '20200102']) == [] and
  (H.FIRST_YEAR, H.MIN_FIT) == (2, 60))

# ---------------------------------------------------------------------
# H5: one market's numbers, on a tape whose range follows the index
# ---------------------------------------------------------------------
rng = random.Random(34)
WD5 = weekdays(D(2019, 1, 1), D(2021, 12, 31))
days5, order5, iv5 = {}, [], []
logiv, prev_iv = math.log(18.0), 18.0
for d in WD5:
    s = ymd(d)
    Rv = prev_iv / 1600.0 * math.exp(rng.gauss(0, 0.15))
    days5[s] = flat(s, 1000.0, 1000.0, {
        100: 1000.0 + 600.0 * Rv,
        150: 1000.0 + 600.0 * Rv * rng.uniform(0.1, 0.9),
        200: 1000.0 - 400.0 * Rv,
        250: 1000.0 - 400.0 * Rv * rng.uniform(0.1, 0.9), 300: 1000.0})
    order5.append(s)
    logiv = 0.97 * logiv + 0.03 * math.log(18.0) + rng.gauss(0, 0.06)
    prev_iv = math.exp(logiv)
    iv5.append((s, prev_iv))
chain5 = [dict(session=s) for s in order5]
high5 = set(order5[::7])
ev5 = collections.OrderedDict((
    ('FOMC', {'20210127', '20210317', '20210428', '19990101'}),
    ('CPI', {'20210113'})))
res5 = H.evaluate(days5, order5, chain5, iv5, high5, ev5)
use5 = H.usable(H.table(days5, order5, iv5))
fit5 = [r for r in use5 if r['session'] < '20210101']
tst5 = [r for r in use5 if r['session'] >= '20210101']
# IMPLIED by hand: one input, the slope is the covariance over the variance
mx = S.mean([r['iv'] for r in fit5])
my = S.mean([r['y'] for r in fit5])
slope = sum((r['iv'] - mx) * (r['y'] - my) for r in fit5) / \
    sum((r['iv'] - mx) ** 2 for r in fit5)
e_iv = [r['y'] - (my + slope * (r['iv'] - mx)) for r in tst5]
ybar = S.mean([r['y'] for r in tst5])
sst5 = sum((r['y'] - ybar) ** 2 for r in tst5)
bh = H.ols([H.MODELS['HAR'](r) for r in fit5], [r['y'] for r in fit5])
bb = H.ols([H.MODELS[H.BEST](r) for r in fit5], [r['y'] for r in fit5])
d5 = [(r['session'],
       (r['y'] - H.predict(bh, H.MODELS['HAR'](r))) ** 2 -
       (r['y'] - H.predict(bb, H.MODELS[H.BEST](r))) ** 2) for r in tst5]
err5 = {r['session']: r['y'] - H.predict(bb, H.MODELS[H.BEST](r))
        for r in tst5}
rv5 = W33.compare([e for s, e in err5.items() if s in high5],
                  [e for s, e in err5.items() if s not in high5])
m5 = res5['models']
# a tape of one shape: the falling and rising variance say nothing new
days5s = {s: flat(s, 1000.0, 1000.0, {
    100: 1000.0 + 600.0 * H.cash_range(days5[s]),
    200: 1000.0 - 400.0 * H.cash_range(days5[s]), 300: 1000.0})
    for s in order5}
res5s = H.evaluate(days5s, order5, chain5, iv5)
t('H5: on a tape whose range follows yesterday\'s index, IMPLIED\'s error '
  'and R2 are those of a slope worked out by hand, d is HAR\'s squared '
  'error less HAR+IMPLIED\'s session by session with its weekly t, and '
  'the options market adds; only the third year is scored',
  res5['scored'] == len(tst5) and res5['usable'] == len(use5) and
  res5['sessions'] == len(order5) and
  res5['forecast_years'] == ['2021', '2021'] and
  res5['first_scored'] == tst5[0]['session'] and
  near(m5['IMPLIED']['loss'], S.mean([e * e for e in e_iv]), 1e-6) and
  near(m5['IMPLIED']['r2'], 1.0 - sum(e * e for e in e_iv) / sst5, 1e-5)
  and list(m5) == ['ATR', 'HAR', 'IMPLIED', 'HAR+IMPLIED'] and
  list(res5['implied']['series']) == [s for s, _v in d5] and
  all(near(res5['implied']['series'][s], v, 1e-8) for s, v in d5) and
  near(res5['implied']['mean'], S.mean([v for _s, v in d5]), 1e-6) and
  res5['implied']['t'] == round(W28.stats(d5)['t'], 3) and
  res5['implied']['mean'] > 0 and res5['implied']['t'] > 2.5 and
  m5['HAR+IMPLIED']['r2'] > m5['HAR']['r2'] and
  m5['IMPLIED']['r2'] > m5['ATR']['r2'] and
  res5['rvmr'] == rv5 and rv5['n_yes'] + rv5['n_no'] == len(tst5) and
  near(res5['error_sd'], S.stdev(list(err5.values())), 1e-5) and
  res5['down']['n'] == len(tst5) and res5['down']['mean'] is not None
  and res5s['down']['n'] == 0 and res5s['down']['mean'] is None and
  res5s['rvmr'] is None and res5s['events'] is None and
  res5s['scored'] == len(tst5) and
  len(res5['fit_all']['coefficients']) == 5 and
  res5['fit_all']['rows'] == len(use5))

# ---------------------------------------------------------------------
# H6: the calendar and the events by hand
# ---------------------------------------------------------------------
CH6 = [dict(session=ymd(d)) for d in weekdays(D(2021, 1, 4), D(2021, 7, 14))]
cal6 = H.calendar(CH6)
pe = os.path.join(WORK, 'events.csv')
with open(pe, 'w') as fh:
    fh.write('date,kind,source\n2021-01-27,FOMC,federalreserve.gov\n'
             '2021-03-17,FOMC,federalreserve.gov\n'
             '2020-03-15,FOMC_UNSCHEDULED,federalreserve.gov\n')
ev6 = H.read_events(pe)
pe_bad = os.path.join(WORK, 'events_bad.csv')
with open(pe_bad, 'w') as fh:
    fh.write('date,kind,source\n2021-01-27,EARNINGS,x\n')
pe_head = os.path.join(WORK, 'events_head.csv')
with open(pe_head, 'w') as fh:
    fh.write('2021-01-27,FOMC,x\n')
k6 = H.by_kind(collections.OrderedDict((('A', {'s1', 's3'}), ('B', set()))),
               collections.OrderedDict((('s1', 0.2), ('s2', 9.0),
                                        ('s3', 0.4))),
               dict(s1=1.0, s2=9.0, s3=2.0))
t('H6: expiry Fridays are the third Friday of a month, the quarterly '
  'ones those of March, June, September and December; a month ends on '
  'its last trading day, and the last day on file ends nothing; an '
  'events file holds only the four kinds, and a kind\'s line is the mean '
  'over its scored sessions',
  cal6['OPEX'] == {'20210115', '20210219', '20210319', '20210416',
                   '20210521', '20210618'} and
  cal6['QOPEX'] == {'20210319', '20210618'} and
  cal6['MONTH_END'] == {'20210129', '20210226', '20210331', '20210430',
                        '20210531', '20210630'} and
  cal6['QUARTER_END'] == {'20210331', '20210630'} and
  list(cal6) == list(H.CALENDAR) and
  H.third_friday('20210115') and not H.third_friday('20210122') and
  not H.third_friday('20210114') and
  ev6 == collections.OrderedDict((
      ('FOMC', {'20210127', '20210317'}),
      ('FOMC_UNSCHEDULED', {'20200315'}))) and
  'holds the kind' in stopped(lambda: H.read_events(pe_bad)) and
  'does not start with' in stopped(lambda: H.read_events(pe_head)) and
  k6['A'] == dict(n=2, error=0.3, excess=1.5) and
  k6['B'] == dict(n=0, error=None, excess=None) and
  res5['calendar']['OPEX']['n'] == 12 and
  res5['calendar']['QOPEX']['n'] == 4 and
  res5['calendar']['MONTH_END']['n'] == 11 and
  res5['calendar']['QUARTER_END']['n'] == 3 and
  res5['events']['FOMC']['n'] == 3 and res5['events']['CPI']['n'] == 1 and
  near(res5['events']['CPI']['error'], err5['20210113'], 1e-5) and
  H.EVENT_KINDS == ('FOMC', 'FOMC_UNSCHEDULED', 'CPI', 'NFP'))


# ---------------------------------------------------------------------
# H7: the verdict
# ---------------------------------------------------------------------
MON = [ymd(D(2021, 1, 4) + _dt.timedelta(days=7 * i)) for i in range(9)]


def rep7(market, values, sessions=None, version=None):
    ser = collections.OrderedDict(zip(sessions or MON, values))
    st = W28.stats(list(ser.items()))
    return dict(
        wave34=version or H.W34_VERSION, part='market', market=market,
        implied=dict(mean=st['mean'], t=st['t'], series=ser),
        models=collections.OrderedDict(
            (k, dict(r2=0.1 * i)) for i, k in enumerate(H.MODELS)))


GOOD = [0.02, 0.03, 0.01, 0.04, 0.02, 0.03, 0.02, 0.03]
BAD = [-0.05, -0.04, -0.06, -0.05, -0.05, -0.04, -0.06, -0.05]
MIX = [0.30, -0.25, 0.28, -0.27, 0.31, -0.26, 0.29, -0.28]
WEAK = [0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002]
v1 = H.decide([rep7('NQ', BAD), rep7('ES', GOOD), rep7('RTY', GOOD)])
v2 = H.decide([rep7('NQ', GOOD), rep7('ES', GOOD), rep7('RTY', BAD)])
v3 = H.decide([rep7('NQ', GOOD), rep7('ES', MIX), rep7('RTY', MIX)])
v4 = H.decide([rep7('NQ', GOOD), rep7('ES', GOOD),
               rep7('RTY', [0.04] * 8 + [0.5], sessions=MON)])
v5 = H.decide([rep7('NQ', GOOD), rep7('ES', GOOD), rep7('RTY', [-0.0001] * 8)])
pool4 = H.pooled([rep7('ES', GOOD), rep7('RTY', [0.04] * 8 + [0.5],
                                        sessions=MON)])
one = [(s, (a + 0.04) / 2.0) for s, a in zip(MON, GOOD)] + [(MON[8], 0.5)]
t('H7: IMPLIED ADDS when d is above 0 on ES and on RTY and, over both, '
  'above 0 with a weekly t of 2.5 or more; a session\'s d over both is '
  'the average of the markets that have it; NQ is told and never judged; '
  'a missing, doubled or foreign report stops',
  v1['status'] == 'IMPLIED ADDS' and v1['starts_from'] == 'HAR+IMPLIED'
  and v1['means']['NQ'] < 0 and v1['pooled']['t'] >= 2.5 and
  v2['status'] == 'DOES NOT ADD' and v2['starts_from'] == 'HAR' and
  v3['status'] == 'DOES NOT ADD' and v3['pooled']['mean'] > 0 and
  v3['pooled']['t'] < 2.5 and
  v5['status'] == 'DOES NOT ADD' and v5['pooled']['mean'] > 0 and
  v5['pooled']['t'] >= 2.5 and
  all(near(a[1], b[1], 1e-12) and a[0] == b[0]
      for a, b in zip(pool4, one)) and len(pool4) == 9 and
  v4['pooled']['n'] == 9 and
  'are needed' in stopped(lambda: H.decide(
      [rep7('ES', GOOD), rep7('RTY', GOOD)])) and
  'are needed' in stopped(lambda: H.decide(
      [rep7('NQ', GOOD), rep7('ES', GOOD), rep7('RTY', GOOD),
       rep7('ES', GOOD)])) and
  'not one of' in stopped(lambda: H.decide(
      [rep7('NQ', GOOD, version='x'), rep7('ES', GOOD),
       rep7('RTY', GOOD)])) and
  'VERDICT: IMPLIED ADDS' in H.text(v1) and
  'starts from HAR+IMPLIED.' in H.text(v1) and
  'VERDICT: DOES NOT ADD' in H.text(v2) and
  'starts from HAR.' in H.text(v2) and
  'NQ is reported, never judged' in H.text(v1) and H.T_BAR == 2.5 and
  H.JUDGED_ON == ('ES', 'RTY'))

# ---------------------------------------------------------------------
# H8: the reads and the ledger
# ---------------------------------------------------------------------
R1 = make_rows(D(2019, 6, 3), D(2021, 10, 22), 11)
FN = write(os.path.join(WORK, 'nq'), 'NQ 12-21.Last.txt', R1)
FE = write(os.path.join(WORK, 'es'), 'ES 12-21.Last.txt', R1)
R5 = make_rows(D(2019, 6, 3), D(2021, 10, 22), 7, tick=0.1, px0=2000.0,
               sd=0.4)
FR = write(os.path.join(WORK, 'rty'), 'RTY 12-21.Last.txt', R5)
rng = random.Random(8)
vals8 = [(d.strftime('%Y-%m-%d'), '.' if i % 61 == 60 else
          '%.2f' % (18.0 + 6.0 * math.sin(i / 9.0) + rng.random()))
         for i, d in enumerate(weekdays(D(2019, 1, 1), D(2026, 11, 25)))]
IVF = {m: iv_file('%s.csv' % H.SERIES[m], H.SERIES[m], vals8)
       for m in H.MARKETS}
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w34_%s.json' % m) for m in H.MARKETS}
rcX, saidX = said_by(lambda: H.main(
    [FE, '--market', 'ES', '--iv', IVF['NQ']], ledger=led))
rcI, saidI = said_by(lambda: H.main([FE, '--market', 'ES'], ledger=led))
rcV, saidV = said_by(lambda: H.main(
    [FE, '--market', 'ES', '--iv', IVF['ES'], '--events', pe_bad],
    ledger=led))
none_yet = not os.path.exists(led)
rcN, saidN = said_by(lambda: H.main(
    [FN, '--market', 'NQ', '--iv', IVF['NQ'], '--out', outs['NQ']],
    ledger=led))
rcE, saidE = said_by(lambda: H.main(
    [FE, '--market', 'ES', '--iv', IVF['ES'], '--events', pe, '--out',
     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: H.main(
    [FR, '--market', 'RTY', '--iv', IVF['RTY'], '--out', outs['RTY']],
    ledger=led))
rcE2, saidE2 = said_by(lambda: H.main(
    [FE, '--market', 'ES', '--iv', IVF['ES']], ledger=led))
files = [outs[m] for m in H.MARKETS]
rcD, saidD = said_by(lambda: H.main(['--decide'] + files))
rcD3, saidD3 = said_by(lambda: H.main(['--decide', outs['ES']]))
rcM, saidM = said_by(lambda: H.main(
    [FN, '--market', 'YM', '--iv', IVF['NQ']], ledger=led))
rcW, saidW = said_by(lambda: H.main(
    [FN, '--market', 'NQ', '--iv', IVF['NQ'], '--out',
     os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'ledger3.json')))
reps8 = {m: json.load(open(outs[m])) for m in H.MARKETS}
ledr = json.load(open(led))['reads']
rdE, _chk = W25.read(FE, 'ES', 'UTC', 'end')
dE, oE, cE = S.build(rdE)
ownE = H.evaluate(dE, oE, cE, H.read_iv(IVF['ES'], 'ES'))
t('H8: NQ, ES and RTY are each read once and recorded before anything '
  'is shown; the report from the command is the pieces\' own; the wrong '
  'index file, no index file or a bad events file stop with nothing '
  'read and nothing recorded; the verdict needs all three markets',
  rcX == 2 and 'needs VIXCLS' in saidX and rcI == 2 and
  'give --iv' in saidI and rcV == 2 and 'holds the kind' in saidV and
  none_yet and rcN == rcE == rcR == 0 and rcE2 == 2 and
  'REFUSED' in saidE2 and
  reps8['ES']['models'] == json.loads(json.dumps(ownE['models'])) and
  reps8['ES']['implied']['mean'] == ownE['implied']['mean'] and
  reps8['ES']['forecast_years'] == ['2021', '2021'] and
  reps8['ES']['index']['series'] == 'VIXCLS' and
  reps8['ES']['index']['last_used'] < reps8['ES']['last_session'] and
  reps8['ES']['events_given'] == ['FOMC', 'FOMC_UNSCHEDULED'] and
  reps8['ES']['events']['FOMC']['n'] == 2 and
  reps8['ES']['events']['FOMC_UNSCHEDULED']['n'] == 0 and
  reps8['NQ']['events'] is None and
  'no events file was given' in saidN and 'event days (' in saidE and
  reps8['NQ']['rvmr']['n_yes'] + reps8['NQ']['rvmr']['n_no'] ==
  reps8['NQ']['scored'] > 150 and
  reps8['NQ']['calendar']['OPEX']['n'] >= 9 and
  'read recorded (1 read(s)' in saidN and
  rcD == 0 and 'VERDICT: ' in saidD and rcD3 == 2 and
  'are needed' in saidD3 and rcM == 2 and rcW == 2 and
  'cannot be written' in saidW and
  not os.path.exists(os.path.join(WORK, 'ledger3.json')) and
  [(r['version'], r['part'], r['market']) for r in ledr] ==
  [(H.W34_VERSION, 'market', m) for m in H.MARKETS] and
  all(r['n'] == reps8[r['market']]['scored'] for r in ledr) and
  CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25))

# ---------------------------------------------------------------------
# H9: what is printed
# ---------------------------------------------------------------------
t('H9: everything printed is plain ASCII and says what it is: a '
  'forecast of the range, not of direction, nothing trades, no order '
  'placed',
  all(max(s.encode('utf-8')) < 128 for s in (saidN, saidE, saidD)) and
  all('No order was placed.' in s and 'not of direction' in s
      for s in (saidN, saidE, saidD)) and
  'R2 out of sample' in saidN and 'RVMR HIGH at 09:35' in saidN and
  'calendar days (' in saidN and 'HAR+IMPLIED fitted on all' in saidN)

# ---------------------------------------------------------------------
# H10: the registration's rules are the code's
# ---------------------------------------------------------------------
t('H10: the 14 sessions, the one, 5 and 22, the 5 calendar days, the '
  'third year, the 2.5, the indices and the markets judged are the '
  'frozen registration\'s',
  H.MARKETS == ('NQ', 'ES', 'RTY') and H.RVMR_MINUTE == 5 and
  all(x in REG for x in (
      'FROZEN on 2026-11-28',
      'of the 390 minutes from 09:30) \u00f7 the open',
      'log of the mean R of the 14 previous eligible sessions',
      'log R of the previous session; log of the mean R of the previous '
      '5; log of the mean R of the previous 22',
      'VXN for NQ, VIX for ES, RVX for RTY',
      'when that is more than 5 calendar days before, the session has no '
      'IMPLIED input',
      'the first forecast year is the third calendar year',
      'the mean of d is above 0 on ES and above 0 on RTY',
      '**weekly t of 2.5 or more**',
      'NQ is reported, never judged',
      'the third Friday of a month',
      'FOMC, FOMC_UNSCHEDULED, CPI, NFP',
      'one-minute log changes of the 390 closes',
      'Sessions from 2026-07-01 are never read')))

shutil.rmtree(WORK, ignore_errors=True)
print('\n%d/%d tests passed' % (sum(1 for _n, ok in OK if ok), len(OK)))
sys.exit(0 if all(ok for _n, ok in OK) else 1)
