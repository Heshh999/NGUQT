#!/usr/bin/env python3
"""mrofyt_range34.py - MROF-YT-W34-RANGE-1.0

MROF_YT_WAVE34_RANGE_REGISTRATION.md turned into running code: how far
the market will move, forecast before the open.

    the quantity   log R, R = the cash session's high less its low over
                   the open
    ATR            the mean R of the last 14 sessions
    HAR            the last session, the last 5 and the last 22
    IMPLIED        the options market's own forecast at the last close:
                   VXN for NQ, VIX for ES, RVX for RTY (FRED's files)
    HAR+IMPLIED    both
    the verdict    IMPLIED ADDS when HAR+IMPLIED beats HAR on ES and on
                   RTY, and over both with a weekly t of 2.5 or more

    python3 mrofyt_range34.py "<NQ exports>" --market NQ --iv VXNCLS.csv
                              [--events events.csv] --out w34_nq.json
    python3 mrofyt_range34.py "<ES exports>" --market ES --iv VIXCLS.csv
                              [--events events.csv] --out w34_es.json
    python3 mrofyt_range34.py "<RTY exports>" --market RTY --iv RVXCLS.csv
                              [--events events.csv] --out w34_rty.json
    python3 mrofyt_range34.py --decide w34_nq.json w34_es.json w34_rty.json
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok

Each year is forecast from a fit on the sessions before it. Each read is
made once and recorded before any result is shown. Read-only; nothing
here trades and no order is placed.
"""
import bisect
import collections
import datetime
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_dealer33 as W33        # noqa: E402
import mrofyt_markets28 as W28       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_sizing31 as Z31        # noqa: E402

W34_VERSION = 'MROF-YT-W34-RANGE-1.0'
REGISTRATION = 'MROF_YT_WAVE34_RANGE_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
N = S.N_MIN
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')
SERIES = {'NQ': 'VXNCLS', 'ES': 'VIXCLS', 'RTY': 'RVXCLS'}
ATR_N, HAR_N = 14, (1, 5, 22)
IV_MAX_AGE = 5                       # calendar days
FIRST_YEAR = 2                       # the third calendar year, from 0
MIN_FIT = 60                         # sessions a fit needs
T_BAR = 2.5
RVMR_MINUTE = 5                      # 09:35
EVENT_KINDS = ('FOMC', 'FOMC_UNSCHEDULED', 'CPI', 'NFP')
CALENDAR = ('OPEX', 'QOPEX', 'MONTH_END', 'QUARTER_END')
QUARTER_MONTHS = ('03', '06', '09', '12')
MODELS = collections.OrderedDict((
    ('ATR', lambda r: [1.0, r['atr']]),
    ('HAR', lambda r: [1.0] + list(r['har'])),
    ('IMPLIED', lambda r: [1.0, r['iv']]),
    ('HAR+IMPLIED', lambda r: [1.0] + list(r['har']) + [r['iv']])))
BEST, DOWN = 'HAR+IMPLIED', 'HAR+IMPLIED+DOWN'


def x_down(r):
    return MODELS[BEST](r) + list(r['down'])


def _date(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


# ---------------------------------------------------------------------
# the files beside the bars
# ---------------------------------------------------------------------
def read_iv(path, market):
    """[(YYYYMMDD, value)] in date order from FRED's file of the
    market's index; a '.' or an empty value is a day without one."""
    want = SERIES[market]
    try:
        with open(path) as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise CX.ContextDataError('the index file cannot be read (%s). '
                                  'Nothing was read.' % exc)
    head = [h.strip().strip('"') for h in lines[0].split(',')] \
        if lines else []
    if len(head) != 2 or head[1] != want:
        raise CX.ContextDataError(
            "%s is not FRED's %s (its first line is %r): %s needs %s. "
            'Nothing was read.' % (os.path.basename(path), want,
                                   lines[0][:40] if lines else '', market,
                                   want))
    out = []
    for ln in lines[1:]:
        p = [x.strip() for x in ln.split(',')]
        try:
            if len(p) != 2:
                raise ValueError(ln)
            day = datetime.datetime.strptime(p[0], '%Y-%m-%d')
            if p[1] in ('.', ''):
                continue
            v = float(p[1])
            if not v > 0:
                raise ValueError(ln)
        except ValueError:
            raise CX.ContextDataError(
                'a line of %s is not "date,value" (%r). Nothing was read.'
                % (os.path.basename(path), ln[:40]))
        out.append((day.strftime('%Y%m%d'), v))
    out.sort()
    if not out:
        raise CX.ContextDataError('%s holds no value. Nothing was read.'
                                  % os.path.basename(path))
    return out


def iv_before(ivs, session, dates=None):
    """The index's last value dated before the session, or None when
    that is more than 5 calendar days before."""
    dates = dates if dates is not None else [d for d, _v in ivs]
    k = bisect.bisect_left(dates, session)
    if k == 0:
        return None
    day, v = ivs[k - 1]
    if (_date(session) - _date(day)).days > IV_MAX_AGE:
        return None
    return v


def read_events(path):
    """{kind: set of YYYYMMDD} from a file of lines date,kind,source
    under that heading."""
    out = collections.OrderedDict()
    try:
        with open(path) as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise CX.ContextDataError('the events file cannot be read (%s). '
                                  'Nothing was read.' % exc)
    if not lines or [h.strip() for h in lines[0].split(',')][:2] != \
            ['date', 'kind']:
        raise CX.ContextDataError(
            'the events file does not start with "date,kind,source". '
            'Nothing was read.')
    for ln in lines[1:]:
        p = [x.strip() for x in ln.split(',')]
        try:
            day = datetime.datetime.strptime(p[0], '%Y-%m-%d')
            kind = p[1]
        except (ValueError, IndexError):
            raise CX.ContextDataError(
                'a line of the events file is not "date,kind,source" (%r). '
                'Nothing was read.' % ln[:40])
        if kind not in EVENT_KINDS:
            raise CX.ContextDataError(
                'the events file holds the kind %r; the kinds are %s. '
                'Nothing was read.' % (kind, ', '.join(EVENT_KINDS)))
        out.setdefault(kind, set()).add(day.strftime('%Y%m%d'))
    return out


def third_friday(session):
    d = _date(session)
    return d.weekday() == 4 and 15 <= d.day <= 21


def calendar(chain):
    """{kind: set of sessions}: option-expiry Fridays, the quarterly
    ones, the last trading day of a month and of a quarter. The last day
    on file is the end of nothing known."""
    ses = [r['session'] for r in chain]
    opex = {s for s in ses if third_friday(s)}
    month_end = {a for a, b in zip(ses, ses[1:]) if a[:6] != b[:6]}
    return collections.OrderedDict((
        ('OPEX', opex),
        ('QOPEX', {s for s in opex if s[4:6] in QUARTER_MONTHS}),
        ('MONTH_END', month_end),
        ('QUARTER_END', {s for s in month_end
                         if s[4:6] in QUARTER_MONTHS})))


# ---------------------------------------------------------------------
# sections 1 and 2: the quantity and the inputs
# ---------------------------------------------------------------------
def cash_range(d):
    """R: the highest high less the lowest low of the 390 minutes, over
    the open."""
    return (max(d.h) - min(d.l)) / d.o


def semis(d):
    """(log RS-, log RS+): the realized variance of the session from its
    falling and from its rising minutes (one-minute log changes of the
    390 closes); None unless both are above 0."""
    dn = up = 0.0
    for a, b in zip(d.c, d.c[1:]):
        x = math.log(b / a)
        if x < 0:
            dn += x * x
        else:
            up += x * x
    return (math.log(dn), math.log(up)) if dn > 0 and up > 0 else None


def table(days, order, ivs):
    """One row a session with a range: dict(session, y = log R, atr,
    har = (day, 5, 22), iv, down), each input None when it does not
    exist. Every input is known at the previous close."""
    seq = [(s, cash_range(days[s])) for s in order]
    seq = [(s, r) for s, r in seq if r > 0]
    dates = [d for d, _v in ivs]
    R = [r for _s, r in seq]
    rows = []
    for i, (s, r) in enumerate(seq):
        v = iv_before(ivs, s, dates)
        rows.append(dict(
            session=s, y=math.log(r),
            atr=math.log(S.mean(R[i - ATR_N:i])) if i >= ATR_N else None,
            har=tuple(math.log(S.mean(R[i - n:i])) for n in HAR_N)
            if i >= HAR_N[-1] else None,
            iv=math.log(v) if v is not None else None,
            down=semis(days[seq[i - 1][0]]) if i >= 1 else None))
    return rows


def usable(rows):
    """The rows on which all four forecasts exist."""
    return [r for r in rows if r['atr'] is not None and
            r['har'] is not None and r['iv'] is not None]


# ---------------------------------------------------------------------
# least squares, and the walk forward
# ---------------------------------------------------------------------
def ols(X, y):
    """The least-squares coefficients, by the normal equations and
    elimination with pivoting. Raises ValueError when the inputs do not
    determine them."""
    k = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(k)] +
         [sum(r[i] * v for r, v in zip(X, y))] for i in range(k)]
    scale = max(abs(A[i][i]) for i in range(k)) or 1.0
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) <= 1e-12 * scale:
            raise ValueError('singular')
        A[c], A[piv] = A[piv], A[c]
        for r in range(k):
            if r != c:
                f = A[r][c] / A[c][c]
                for j in range(c, k + 1):
                    A[r][j] -= f * A[c][j]
    return [A[i][k] / A[i][i] for i in range(k)]


def predict(b, x):
    return sum(p * q for p, q in zip(b, x))


def forecast_years(order):
    """The calendar years that are forecast: from the third one of the
    market's sessions."""
    return sorted({s[:4] for s in order})[FIRST_YEAR:]


def fit(rows, x_of, what):
    if len(rows) < MIN_FIT:
        raise CX.ContextDataError(
            'only %d sessions to fit %s on: at least %d are needed. '
            'Nothing was computed.' % (len(rows), what, MIN_FIT))
    try:
        return ols([x_of(r) for r in rows], [r['y'] for r in rows])
    except ValueError:
        raise CX.ContextDataError(
            'the inputs of %s do not determine a fit. Nothing was '
            'computed.' % what)


def walk(rows, years, x_of, what):
    """{session: forecast of log R}: each year from the fit on every row
    before that year."""
    out = collections.OrderedDict()
    for y in years:
        test = [r for r in rows if r['session'][:4] == y]
        if not test:
            continue
        b = fit([r for r in rows if r['session'][:4] < y], x_of,
                '%s before %s' % (what, y))
        for r in test:
            out[r['session']] = predict(b, x_of(r))
    return out


# ---------------------------------------------------------------------
# sections 3 and 4: the losses and what is reported beside
# ---------------------------------------------------------------------
def _r(x, n=6):
    return None if x is None else round(x, n)


def paired(pairs):
    """The mean and the weekly t of a session-by-session difference."""
    st = W28.stats(pairs)
    return dict(n=st['n'], mean=_r(st['mean'], 7), t=_r(st['t'], 3),
                weeks=st['weeks'])


def by_kind(kinds, err, excess):
    """For each kind of day: the scored sessions of it, the forecast's
    mean error on them and their mean log R less the overall mean."""
    out = collections.OrderedDict()
    for k, days in kinds.items():
        ses = [s for s in err if s in days]
        out[k] = dict(n=len(ses),
                      error=_r(S.mean([err[s] for s in ses]), 5)
                      if ses else None,
                      excess=_r(S.mean([excess[s] for s in ses]), 5)
                      if ses else None)
    return out


def evaluate(days, order, chain, ivs, high=None, events=None):
    """Everything of one market from its eligible sessions, the index's
    values, the sessions that are RVMR HIGH at 09:35 and the events."""
    rows = usable(table(days, order, ivs))
    years = forecast_years(order)
    if not years:
        raise CX.ContextDataError(
            'the sessions span fewer than three calendar years: no year '
            'can be forecast. Nothing was computed.')
    y = collections.OrderedDict(
        (r['session'], r['y']) for r in rows if r['session'][:4] in years)
    if len(y) < 2:
        raise CX.ContextDataError(
            'no session can be scored: does the index file cover the '
            'exports? Nothing was computed.')
    fc = collections.OrderedDict(
        (name, walk(rows, years, x_of, name))
        for name, x_of in MODELS.items())
    mean_y = S.mean(list(y.values()))
    sst = sum((v - mean_y) ** 2 for v in y.values())
    loss = {name: {s: (y[s] - f[s]) ** 2 for s in y}
            for name, f in fc.items()}
    models = collections.OrderedDict()
    for name in MODELS:
        sse = sum(loss[name].values())
        models[name] = dict(n=len(y), loss=_r(sse / len(y), 7),
                            r2=_r(1.0 - sse / sst, 5) if sst > 0 else None)
    d = [(s, loss['HAR'][s] - loss[BEST][s]) for s in y]
    implied = paired(d)
    implied['series'] = collections.OrderedDict(
        (s, round(v, 9)) for s, v in d)
    try:                                 # reported only: never stops
        f_dn = walk([r for r in rows if r['down'] is not None], years,
                    x_down, DOWN)
    except CX.ContextDataError:
        f_dn = {}
    down = paired([(s, loss[BEST][s] - (y[s] - f_dn[s]) ** 2)
                   for s in y if s in f_dn])
    err = collections.OrderedDict((s, y[s] - fc[BEST][s]) for s in y)
    excess = {s: y[s] - mean_y for s in y}
    rvmr = None
    if high is not None:
        rvmr = W33.compare([err[s] for s in err if s in high],
                           [err[s] for s in err if s not in high])
    b_all = fit(rows, MODELS[BEST], BEST)
    return dict(
        sessions=len(order), usable=len(rows), scored=len(y),
        forecast_years=[years[0], years[-1]],
        first_scored=next(iter(y)), last_scored=list(y)[-1],
        models=models, implied=implied,
        har_vs_atr=paired([(s, loss['ATR'][s] - loss['HAR'][s])
                           for s in y]),
        down=down, rvmr=rvmr,
        error_sd=_r(S.stdev(list(err.values())), 5),
        calendar=by_kind(calendar(chain), err, excess),
        events=by_kind(events, err, excess) if events else None,
        fit_all=dict(rows=len(rows), inputs=['1', 'log R day',
                                             'log R 5', 'log R 22',
                                             'log index'],
                     coefficients=[_r(b, 6) for b in b_all]))


# ---------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------
def run_market(path, market, iv_path, events_path=None, stamps_tz='UTC',
               stamps='end', gaps_ok=False):
    if market not in MARKETS:
        raise CX.ContextDataError('--market is one of %s'
                                  % ', '.join(MARKETS))
    Z31.rvmr_unchanged()
    ivs = read_iv(iv_path, market)
    events = read_events(events_path) if events_path else None
    rd, chk = W25.read(path, market, stamps_tz, stamps)
    days, order, chain = S.build(rd)
    if len(order) < W25.MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d usable %s sessions: this needs years of minute bars. '
            'Nothing was computed.' % (len(order), market))
    g = W25.gaps(chain)
    if g and not gaps_ok:
        raise CX.ContextDataError(
            'the %s exports have no cash session between %s: a contract was '
            'not exported. Nothing was computed. Export it and run again; '
            'if the feed has no bars for those days, add --gaps-ok.'
            % (market, W25._gap_text(g)))
    st = Z31.states(rd, chain, order)
    high = {s for s in order if st[s][RVMR_MINUTE]['rvmr'] == 'HIGH'}
    res = evaluate(days, order, chain, ivs, high, events)
    rep = dict(
        wave34=W34_VERSION, registration=REGISTRATION, part='market',
        market=market, files=len(rd.files), stamp_check=chk,
        first_session=order[0], last_session=order[-1],
        gaps=[list(x) for x in g],
        index=dict(series=SERIES[market], first=ivs[0][0],
                   last_used=max(d for d, _v in ivs
                                 if d < order[-1]) if ivs[0][0] < order[-1]
                   else None),
        events_given=sorted(events) if events else [])
    rep.update(res)
    return rep


# ---------------------------------------------------------------------
# section 3: the verdict
# ---------------------------------------------------------------------
def pooled(reps):
    """d over ES and RTY together: a session's d is the average of the
    markets that have it."""
    by = collections.defaultdict(list)
    for r in reps:
        for s, v in r['implied']['series'].items():
            by[s].append(v)
    return [(s, S.mean(v)) for s, v in sorted(by.items())]


def decide(reps):
    for r in reps:
        if r.get('wave34') != W34_VERSION:
            raise CX.ContextDataError('a report is not one of %s. Nothing '
                                      'was decided.' % W34_VERSION)
    by = {r['market']: r for r in reps}
    missing = [m for m in MARKETS if m not in by]
    if missing or len(by) != len(reps):
        raise CX.ContextDataError(
            'the reports of %s are needed, each once. Nothing was decided.'
            % ', '.join(missing or MARKETS))
    means = collections.OrderedDict(
        (m, by[m]['implied']['mean']) for m in MARKETS)
    both = paired(pooled([by[m] for m in JUDGED_ON]))
    adds = bool(
        all(means[m] is not None and means[m] > 0 for m in JUDGED_ON) and
        both['mean'] is not None and both['mean'] > 0 and
        both['t'] is not None and both['t'] >= T_BAR)
    return dict(
        wave34=W34_VERSION, part='decide', means=means, pooled=both,
        status='IMPLIED ADDS' if adds else 'DOES NOT ADD',
        starts_from=BEST if adds else 'HAR',
        r2=collections.OrderedDict(
            (m, collections.OrderedDict(
                (k, v['r2']) for k, v in by[m]['models'].items()))
            for m in MARKETS),
        nq=dict(mean=means['NQ'], t=by['NQ']['implied']['t']))


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _f(x, fmt='%+.4f'):
    return 'n/a' if x is None else fmt % x


def _kinds_text(title, kinds):
    L = ['', '  %s (error = log R less the forecast; excess = log R less '
         'its mean):' % title,
         '  kind              sessions     error    excess']
    for k, v in kinds.items():
        L.append('  %-16s  %8d  %8s  %8s' % (
            k, v['n'], _f(v['error'], '%+.3f'), _f(v['excess'], '%+.3f')))
    return L


def text(rep):
    L = []
    if rep['part'] == 'market':
        ix = rep['index']
        L += ['%s  %s  (%s .. %s)' % (rep['wave34'], rep['market'],
                                      rep['first_session'],
                                      rep['last_session']),
              'How far: forecasts of the log of the cash range, each year '
              'from a fit on the years before.',
              '  index %s; %d sessions, %d with every input, %d scored '
              '(%s .. %s)' % (ix['series'], rep['sessions'], rep['usable'],
                              rep['scored'], rep['first_scored'],
                              rep['last_scored']), '',
              '  forecast       mean squared error   R2 out of sample']
        for name, v in rep['models'].items():
            L.append('  %-13s  %18s  %17s' % (
                name, _f(v['loss'], '%.5f'), _f(v['r2'], '%+.4f')))
        d, h, w = rep['implied'], rep['har_vs_atr'], rep['down']
        L += ['', '  what the options market adds to HAR (d, above 0 when it '
              'helps): mean %s, weekly t %s' % (_f(d['mean'], '%+.6f'),
                                                _f(d['t'], '%+.2f')),
              '  HAR against ATR: mean %s, weekly t %s' % (
                  _f(h['mean'], '%+.6f'), _f(h['t'], '%+.2f')),
              '  downside volatility on top (%d sessions): mean %s, weekly '
              't %s' % (w['n'], _f(w['mean'], '%+.6f'), _f(w['t'], '%+.2f'))]
        rv = rep['rvmr']
        if rv:
            L.append('  RVMR HIGH at 09:35: error %s (%d sessions) against '
                     '%s (%d); Welch t %s' % (
                         _f(rv['mean_yes'], '%+.3f'), rv['n_yes'],
                         _f(rv['mean_no'], '%+.3f'), rv['n_no'],
                         _f(rv['t'], '%+.2f')))
        L += _kinds_text('calendar days', rep['calendar'])
        if rep['events']:
            L += _kinds_text('event days', rep['events'])
        else:
            L += ['', '  event days: no events file was given.']
        fa = rep['fit_all']
        L += ['', '  HAR+IMPLIED fitted on all %d sessions: %s' % (
            fa['rows'], ', '.join('%s %s' % (n, _f(c, '%+.4f'))
                                  for n, c in zip(fa['inputs'],
                                                  fa['coefficients']))),
            '  the spread of its errors out of sample: %s (in logs)'
            % _f(rep['error_sd'], '%.4f')]
    else:
        L.append('What the options market adds to HAR: ' + ', '.join(
            '%s %s' % (m, _f(v, '%+.6f')) for m, v in rep['means'].items()))
        p = rep['pooled']
        L += ['ES and RTY together: mean %s, weekly t %s over %d weeks '
              '(the bar: above 0 on each, t of %.1f)' % (
                  _f(p['mean'], '%+.6f'), _f(p['t'], '%+.2f'), p['weeks'],
                  T_BAR),
              'VERDICT: %s' % rep['status'],
              "  The describing tool's expected range starts from %s."
              % rep['starts_from'],
              '  NQ is reported, never judged: mean %s, weekly t %s'
              % (_f(rep['nq']['mean'], '%+.6f'),
                 _f(rep['nq']['t'], '%+.2f')), '',
              '  R2 out of sample   ' + '  '.join(
                  '%11s' % k for k in MODELS)]
        for m, v in rep['r2'].items():
            L.append('  %-17s  ' % m + '  '.join(
                '%11s' % _f(v[k], '%+.4f') for k in MODELS))
    L.append('A forecast of the range, not of direction; nothing here '
             'trades. No order was placed.')
    return '\n'.join(L)


def read_made(path, market):
    return any(r.get('version') == W34_VERSION and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W34_VERSION, part=rep['part'], market=rep['market'],
        first=rep['first_session'], last=rep['last_session'],
        n=rep['scored'],
        at=datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')))
    try:
        with open(path, 'w') as fh:
            json.dump(doc, fh, indent=1)
    except OSError as exc:
        raise CX.ContextDataError(
            'the ledger %s cannot be written (%s): no result is shown '
            'before the read is on record.' % (os.path.basename(path), exc))
    return len(doc['reads'])


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    if '--decide' in argv:
        files = argv[argv.index('--decide') + 1:]
        try:
            reps = []
            for f in files:
                with open(f) as fh:
                    reps.append(json.load(fh))
            rep = decide(reps)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print('STOPPED: cannot read the reports (%s).' % exc)
            return 2
        except CX.ContextDataError as exc:
            print('STOPPED: %s' % exc)
            return 2
        print(text(rep))
        return 0
    if argv[0].startswith('--'):
        print(__doc__)
        return 2
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    market = (arg('--market') or '').upper()
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    if market not in MARKETS:
        print('STOPPED: --market is one of %s.' % ', '.join(MARKETS))
        return 2
    if not arg('--iv'):
        print("STOPPED: give --iv, FRED's file of %s for %s. Nothing was "
              'read.' % (SERIES[market], market))
        return 2
    out = arg('--out')
    if out and not W25.can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    try:
        if read_made(ledger, market):
            print('REFUSED: this wave has read %s (%s). Each read is made '
                  'once.' % (market, HISTORY_LEDGER))
            return 2
        rep = run_market(argv[0], market, arg('--iv'), arg('--events'),
                         stz, stp, '--gaps-ok' in argv)
        n = record_read(rep, ledger)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-thirty-four report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
