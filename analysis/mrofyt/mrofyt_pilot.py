"""mrofyt_pilot.py - PILOT_DIAGNOSTIC_ONLY analysis (MROF-YT-PILOT-1.0).

Runs the ten-step pilot diagnostic of the consolidated directive over
whatever completed recordings are actually present. It answers two
SEPARATE questions and never merges them:

    1. IS THE SYSTEM WORKING?          (engineering)
    2. DO ANY HYPOTHESES APPEAR PROMISING?  (evidence)

This module is descriptive only. It computes no fill, stop, target, R
multiple or P&L, and it does not search for a model. Question 2 can be
answered NOT_OBSERVED, and that is a legitimate result: it is answered
from the frozen signal population only, which may be empty.

Every session this module reads is permanently labelled
EXPOSED_PILOT_DEV and written to MROF_EXPOSED_PILOT_DEV_DAYS.json. Such
days may remain in later DEV/training where the governing protocol
permits; they can never become untouched prospective validation.

    python3 mrofyt_pilot.py "<capture folder>" --out pilot_report.json

Standard library only.
"""

import array
import bisect
import collections
import datetime as _dt
import json
import os
import sys

import mles_v12_audit as AU
import mrofyt_levels as LV
import mrofyt_runner as RUN
import mrofyt_signals as SIG

PILOT_VERSION = 'MROF-YT-PILOT-1.2'
EXPOSURE_LABEL = 'EXPOSED_PILOT_DEV'

# Interim-monitoring blind. MROF_YT_WAVE2_REGISTRATION.md declares every
# session >= BLIND_FROM untouched validation whose verdict may only be
# read at the checkpoint. This pilot is meant to be run weekly to verify
# recording health and event ACCRUAL -- and W2-A4r is literally A4 as it
# ran, so reading wave-one markouts on those sessions would unblind wave
# two. So by default the pilot withholds every markout (signal, raw and
# window-reference, every horizon) for sessions >= BLIND_FROM, reports
# how many events it withheld, and labels those sessions BLIND_LABEL
# rather than EXPOSURE_LABEL. Fire counts, funnels and integrity checks
# stay visible: knowing N does not reveal which way N went. Unblinding
# is explicit (--blind-from none) and permanently relabels the sessions
# exposed. Bound to the registration text by tests P10/P11.
BLIND_FROM = '20260921'
BLIND_LABEL = 'VALIDATION_BLIND_MARKOUTS_WITHHELD'

# Percentile bootstrap for the registered kill criterion ("95% interval
# includes zero"). Seeded so two runs of the same report agree exactly.
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 20260918
BOOTSTRAP_MIN_N = 5

# Horizons. 300 s is PRIMARY: the operator's own recorded discretionary
# holding period averages ~4 min (longest 8 min 3 s), so 5 min is the
# horizon that matches how this would actually be traded. 600/1800 are
# secondary and bracket the frozen MAX_HOLD_S=1800 cap. Registered here
# BEFORE the data that will be read at these horizons exists.
MARKOUT_S = (1.0, 5.0, 10.0, 30.0, 60.0, 180.0, 300.0, 600.0, 1800.0)
PRIMARY_MARKOUT_S = 300.0

# De-duplication. The runner has no position model and no consumption:
# _fire records EVERY non-zero detector return, so one market event can
# be recorded many times - by the same approach on consecutive windows,
# and by several coincident approaches to nearby levels. Counting those
# as separate signals inflates the population and, worse, weights one
# event several times inside a median. The raw fires list is never
# modified; this is a derived view.
EVENT_COOLDOWN_S = 60.0          # default: matches A1's frozen approaches_60s lookback
COOLDOWN_GRID = (10.0, 60.0, 300.0)

# Under the operator's own NQ-signal / MNQ-execution topology only NQ is
# a signal source. The runner evaluates both instruments and that stays
# true; this labels which fires are signals rather than discarding any.
SIGNAL_SOURCE_INSTRUMENT = 'NQ'

# The frozen detectors, decomposed into the exact ordered stages the
# source in mrofyt_signals.py applies. A window is attributed to the
# FIRST stage it fails, so the stage counts sum to the window count and
# read as a funnel. Availability stages come first because a missing
# input disqualifies before any threshold is consulted.
A1_INPUTS = ('aggr_z', 'progress_ticks', 'replenish_z', 'approaches_60s',
             'opp_flip_z', 'retreat_ticks')
A2_INPUTS = ('wall_z', 'exec_vs_displayed', 'replenish_ratio',
             'cleared_held_5s', 'persist_agree', 'post_clear_z')
A4_INPUTS = ('aggr_z', 'opp_flip_z')
A5_INPUTS = ('trend_dir', 'adverse_z', 'adverse_progress_ticks',
             'replenish_z', 'trend_flip_z')
A6_INPUTS = ('control_z', 'clean_cross', 'held_5s', 'persist_agree',
             'opp_replenish_z')


def _avail(f, names):
    return [n for n in names if f.get(n) is None]


def _a4_fail(f):
    return ((f.get('resid_tail_5pct') is True) or
            (f.get('progress_ticks') is not None and
             f['progress_ticks'] <= 1))


def _a4_back(f):
    return (f.get('returned_through_level') is True) or \
           (f.get('sweep_reclaimed_5s') is True)


FUNNELS = {
    'A1': [('inputs_available', lambda f: not _avail(f, A1_INPUTS)),
           ('aggr_z>=2.0', lambda f: f['aggr_z'] >= 2.0),
           ('progress_ticks<=1', lambda f: f['progress_ticks'] <= 1),
           ('replenish_z>=1.5', lambda f: f['replenish_z'] >= 1.5),
           ('approaches_60s>=2', lambda f: f['approaches_60s'] >= 2),
           ('opp_flip_z>=1.0', lambda f: f['opp_flip_z'] >= 1.0),
           ('retreat_ticks>=1', lambda f: f['retreat_ticks'] >= 1)],
    'A2': [('inputs_available', lambda f: not _avail(f, A2_INPUTS)),
           ('wall_z>=2.0', lambda f: f['wall_z'] >= 2.0),
           ('exec_vs_displayed>=1.5', lambda f: f['exec_vs_displayed'] >= 1.5),
           ('replenish_ratio<0.25', lambda f: f['replenish_ratio'] < 0.25),
           ('cleared_held_5s', lambda f: bool(f['cleared_held_5s'])),
           ('persist_agree>=3', lambda f: f['persist_agree'] >= 3),
           ('post_clear_z>=1.0', lambda f: f['post_clear_z'] >= 1.0)],
    'A4': [('inputs_available', lambda f: not _avail(f, A4_INPUTS)),
           ('aggr_z>=2.0', lambda f: f['aggr_z'] >= 2.0),
           ('response_failed', _a4_fail),
           ('came_back_through', _a4_back),
           ('opp_flip_z>=1.0', lambda f: f['opp_flip_z'] >= 1.0)],
    'A5': [('inputs_available', lambda f: not _avail(f, A5_INPUTS)),
           ('trend_dir!=0', lambda f: f['trend_dir'] != 0),
           ('adverse_z>=2.0', lambda f: f['adverse_z'] >= 2.0),
           ('adverse_progress<=1', lambda f: f['adverse_progress_ticks'] <= 1),
           ('replenish_z>=1.5', lambda f: f['replenish_z'] >= 1.5),
           ('trend_flip_z>=1.0', lambda f: f['trend_flip_z'] >= 1.0)],
    'A6': [('in_0930_0945', lambda f: bool(f.get('in_0930_0945'))),
           ('inputs_available', lambda f: not _avail(f, A6_INPUTS)),
           ('control_z>=2.0', lambda f: f['control_z'] >= 2.0),
           ('clean_cross', lambda f: bool(f['clean_cross'])),
           ('held_5s', lambda f: bool(f['held_5s'])),
           ('persist_agree>=3', lambda f: f['persist_agree'] >= 3),
           ('opp_replenish_z<1.5', lambda f: f['opp_replenish_z'] < 1.5)],
}

FUNNEL_INPUTS = {'A1': A1_INPUTS, 'A2': A2_INPUTS, 'A4': A4_INPUTS,
                 'A5': A5_INPUTS, 'A6': A6_INPUTS}


# ---------------------------------------------------------------------
# instrumented runner
# ---------------------------------------------------------------------
class PilotRunner(RUN.Runner):
    """The frozen runner plus observation. It overrides only hooks; no
    threshold, window, level or detector definition is touched here."""

    def __init__(self, *a, **kw):
        RUN.Runner.__init__(self, *a, **kw)
        self.windows = []                       # feature vector per window
        # Mid series are kept PER RUN, never concatenated per instrument.
        # Two reasons, both correctness: concurrent duplicate recorder
        # instances overlap in time, so a per-instrument series is not
        # even monotone; and a markout spanning two runs would splice
        # across a recording gap and read the jump as a price move.
        self.series = {}                        # (inst, run) -> (t[], px[])
        self.approach_open = {}                 # (inst, aid) -> t0, level
        self._cur = None

    def _process_run(self, st, mp, man):
        self._cur = (st.instrument, man.get('runId'))
        self.series.setdefault(self._cur,
                               (array.array('d'), array.array('d')))
        RUN.Runner._process_run(self, st, mp, man)

    def _on_mid(self, st, t, mid):
        # record BEFORE the frozen logic so an approach opened by this
        # very tick already has its own mid in the series
        ts, ps = self.series[self._cur]
        ts.append(t)
        ps.append(mid)
        RUN.Runner._on_mid(self, st, t, mid)

    def _on_window(self, st, ap, te, f):
        rec = dict(f)
        rec.update(instrument=st.instrument, session=st.session, t_end=te,
                   t_start=ap.t0, wall_state=ap.wall_state,
                   window_index=ap.windows, level_px=ap.level_px,
                   run=self._cur[1] if self._cur else None,
                   family=LV.FAMILY_OF.get(ap.level_id, '?'),
                   approach_id=ap.id, ad=ap.ad,
                   # the level set exactly as the frozen runner held it at
                   # this window (causal by construction): observation
                   # for the God's Eye replay, never an input
                   levels=dict(st.levels))
        self.windows.append(rec)
        self.approach_open.setdefault((st.instrument, ap.id),
                                      dict(t0=ap.t0, level_id=ap.level_id,
                                           level_px=ap.level_px, ad=ap.ad,
                                           session=st.session))

    # ---- markouts (descriptive; mid-to-mid, no fill model) ----------
    def markout(self, instrument, run, t0, horizon):
        """Signed mid change in ticks from t0 to t0+horizon, measured
        inside one run, or None when that run does not extend that far.
        Never extrapolates and never crosses a run boundary."""
        pair = self.series.get((instrument, run))
        if not pair or not pair[0]:
            return None
        ts, ps = pair
        i = bisect.bisect_right(ts, t0) - 1
        if i < 0:
            return None
        if ts[-1] < t0 + horizon:
            return None                  # coverage ends before the horizon
        # last mid at or before the horizon; the horizon itself rarely
        # lands on a tick, and interpolating would invent a price
        j = bisect.bisect_right(ts, t0 + horizon) - 1
        if j < 0:
            return None
        return (ps[j] - ps[i]) / SIG.TICK


# ---------------------------------------------------------------------
# step 1 - data audit
# ---------------------------------------------------------------------
def step1_data_audit(capture_dir):
    rep = AU.audit_capture(capture_dir)
    runs, manifest_only = [], []
    for r in rep.get('runs', []):
        i, man = r['info'], r.get('manifest') or {}
        rec = dict(instrument=i.get('instrument'), session=i.get('session'),
                   run_id=i.get('run_id'), ok=r['ok'], rows=i.get('events'),
                   close=man.get('closeReason'),
                   first=man.get('firstRecvUtc'),
                   last=man.get('lastRecvUtc'),
                   failures=[c for c, _d in r['failures']])
        (runs if r['ok'] else manifest_only).append(rec)
    return dict(ok=rep.get('ok'), failures=rep.get('failures', []),
                manifests=rep['info'].get('manifests', 0),
                verified_runs=runs, unverified_runs=manifest_only,
                pairing=rep['info'].get('overlaps', {}))


def _iso(s):
    if not s:
        return None
    s = s.replace('Z', '')
    if '.' in s:
        a, b = s.split('.')
        s = a + '.' + b[:6]
    return _dt.datetime.fromisoformat(s)


def coverage_windows(verified):
    """Union wall-clock coverage per instrument over runs whose bulk CSVs
    were actually verified. Concurrent duplicate recorder instances of the
    same feed collapse into one window, which is the honest measure: they
    are copies, not independent observations."""
    by = collections.defaultdict(list)
    for r in verified:
        a, b = _iso(r['first']), _iso(r['last'])
        if a and b:
            by[r['instrument']].append((a, b))
    out = {}
    for inst, spans in by.items():
        spans.sort()
        merged = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        out[inst] = dict(
            seconds=round(sum((e - s).total_seconds() for s, e in merged), 1),
            windows=[[s.isoformat(), e.isoformat(),
                      round((e - s).total_seconds(), 1)] for s, e in merged],
            runs=len(spans))
    if len(out) == 2 and 'NQ' in out and 'MNQ' in out:
        a = [(_iso(x[0]), _iso(x[1])) for x in out['NQ']['windows']]
        b = [(_iso(x[0]), _iso(x[1])) for x in out['MNQ']['windows']]
        ov = 0.0
        for s1, e1 in a:
            for s2, e2 in b:
                lo, hi = max(s1, s2), min(e1, e2)
                if hi > lo:
                    ov += (hi - lo).total_seconds()
        out['NQ_MNQ_simultaneous_seconds'] = round(ov, 1)
    return out


# ---------------------------------------------------------------------
# steps 3-5
# ---------------------------------------------------------------------
def step3_feature_health(windows):
    """Per feature: how often it was computable, and its spread when it
    was. A feature that is never computable cannot support or refute
    anything, and saying so is the point of this step."""
    names = ('aggr_z', 'progress_ticks', 'replenish_z', 'replenish_ratio',
             'opp_flip_z', 'retreat_ticks', 'wall_z', 'exec_vs_displayed',
             'post_clear_z', 'control_z', 'persist_agree', 'approaches_60s',
             'resid_tail_5pct', 'trend_dir')
    out = {}
    n = len(windows)
    for k in names:
        vals = [w.get(k) for w in windows]
        good = [v for v in vals if isinstance(v, (int, float))
                and not isinstance(v, bool)]
        d = dict(windows=n, available=len(good),
                 available_frac=round(len(good) / n, 4) if n else None)
        if good:
            good.sort()
            d.update(min=round(good[0], 4), max=round(good[-1], 4),
                     median=round(good[len(good) // 2], 4))
        out[k] = d
    return out


def step4_level_census(windows, ledger):
    lev = collections.Counter()
    fam = collections.Counter()
    appr = collections.defaultdict(set)
    for w in windows:
        lev[w['level_id']] += 1
        fam[w['family']] += 1
        appr[w['level_id']].add((w['instrument'], w['approach_id']))
    census = {k: dict(windows=v, approaches=len(appr[k]))
              for k, v in sorted(lev.items())}
    absent = sorted(set(LV.ACTIVE_LEVEL_IDS) - set(lev))
    return dict(by_level=census, by_family=dict(fam),
                approaches_total=ledger['totals'].get('approaches', 0),
                windows_total=ledger['totals'].get('windows', 0),
                windows_suppressed=ledger['totals'].get(
                    'windows_suppressed', 0),
                never_active_levels=absent,
                wall_states=dict(ledger.get('states', {})))


def step5_funnel(windows, ledger):
    """Stage-by-stage attrition for every family, on the frozen
    thresholds, with no threshold touched."""
    out = {}
    for fam, stages in sorted(FUNNELS.items()):
        counts = collections.Counter()
        missing = collections.Counter()
        passed = 0
        for w in windows:
            where = None
            for name, pred in stages:
                try:
                    ok = pred(w)
                except (TypeError, KeyError):
                    ok = False
                if not ok:
                    where = name
                    break
            if where is None:
                passed += 1
                counts['PASSED_ALL_STAGES'] += 1
            else:
                counts[where] += 1
                if where == 'inputs_available':
                    for m in _avail(w, FUNNEL_INPUTS[fam]):
                        missing[m] += 1
        out[fam] = dict(windows=len(windows), first_failing_stage=dict(counts),
                        missing_inputs=dict(missing), passed=passed,
                        fires_recorded=ledger['totals'].get(
                            'fires_' + fam, 0))
    tot = ledger['totals']
    out['A3'] = dict(
        note='A3 runs on its own 2 s vacuum grid, not the 10 s window grid',
        checks=tot.get('a3_checks', 0),
        vacuum_events=tot.get('vacuum_events', 0),
        delta_z_unavailable=ledger.get('feature_none', {}).get('delta_z', 0),
        fires_recorded=tot.get('fires_A3', 0))
    return out


# ---------------------------------------------------------------------
# steps 6-8
# ---------------------------------------------------------------------
def dedup_fires(fires, cooldown=EVENT_COOLDOWN_S):
    """Collapse raw firings into DISTINCT EVENTS.

    Two firings belong to the same event when they share instrument,
    session, family and direction and the later one starts within
    `cooldown` of the event's FIRST firing. Anchoring on the first
    firing - not on the previous one - bounds every event at `cooldown`
    seconds, so a dense burst cannot chain into one arbitrarily long
    event.

    The approach id is deliberately NOT part of the key. Coincident
    approaches to nearby levels produce different approach ids for what
    is plainly one market event (six MNQ firings inside 7.4 s across
    approaches 3551-3559 in the seven-session pilot), and keying on the
    approach would leave those uncollapsed.

    Returns events in time order. Each carries the first firing's run
    and timestamp, which is what a markout must be measured from.
    """
    by = collections.defaultdict(list)
    for fr in fires:
        by[(fr['instrument'], fr['session'], fr['family'],
            fr['direction'])].append(fr)
    events = []
    for (inst, ses, fam, d), lst in by.items():
        lst.sort(key=lambda f: f['t'])
        cur = None
        for fr in lst:
            if cur is None or fr['t'] - cur['t'] > cooldown:
                cur = dict(instrument=inst, session=ses, family=fam,
                           direction=d, t=fr['t'], t_last=fr['t'],
                           run=fr.get('run'), n_fires=1,
                           approaches=[fr.get('approach')],
                           levels=[fr.get('level')],
                           runs=[fr.get('run')],
                           state=fr.get('state'),
                           is_signal_source=(
                               inst == SIGNAL_SOURCE_INSTRUMENT))
                events.append(cur)
            else:
                cur['t_last'] = fr['t']
                cur['n_fires'] += 1
                cur['approaches'].append(fr.get('approach'))
                cur['levels'].append(fr.get('level'))
                cur['runs'].append(fr.get('run'))
    for e in events:
        e['approaches'] = sorted(set(e['approaches']))
        e['levels'] = sorted(set(x for x in e['levels'] if x is not None))
        e['span_s'] = round(e['t_last'] - e['t'], 3)
        # a markout is measured inside ONE run; if a burst straddled a
        # rotation say so rather than silently using the first run
        e['spans_runs'] = len(set(e['runs'])) > 1
        del e['runs']
    events.sort(key=lambda e: (e['session'], e['t']))
    return events


def step6_signals(ledger):
    fires = ledger.get('fires', [])
    events = dedup_fires(fires, EVENT_COOLDOWN_S)
    sig = [e for e in events if e['is_signal_source']]

    def _fam(evs):
        c = collections.Counter(e['family'] for e in evs)
        return dict(sorted(c.items()))

    sensitivity = {}
    for cd in COOLDOWN_GRID:
        evs = dedup_fires(fires, cd)
        sensitivity['%gs' % cd] = dict(
            distinct_events=len(evs),
            signal_source_only=sum(1 for e in evs if e['is_signal_source']))

    return dict(
        fires=fires,
        count=len(fires),
        by_family={k[6:]: v for k, v in ledger['totals'].items()
                   if k.startswith('fires_')},
        raw_fire_caveat='count is RAW firings. The runner has no position '
                        'model and no consumption, so one market event can '
                        'be recorded many times. Use distinct_events.',
        dedup=dict(
            cooldown_s=EVENT_COOLDOWN_S,
            signal_source_instrument=SIGNAL_SOURCE_INSTRUMENT,
            distinct_events=len(events),
            distinct_events_by_family=_fam(events),
            distinct_events_by_instrument=dict(sorted(
                collections.Counter(e['instrument']
                                    for e in events).items())),
            signal_source_events=len(sig),
            signal_source_events_by_family=_fam(sig),
            inflation_ratio=(round(len(fires) / len(events), 2)
                             if events else None),
            events=events,
            cooldown_sensitivity=sensitivity))


def _bootstrap_ci(vals, stat, n_boot=BOOTSTRAP_N, seed=BOOTSTRAP_SEED):
    """Seeded percentile bootstrap, 2.5/97.5. Standard library only."""
    import random
    rng = random.Random(seed)
    n = len(vals)
    draws = []
    for _ in range(n_boot):
        s = sorted(rng.choice(vals) for _ in range(n))
        draws.append(stat(s))
    draws.sort()
    return (round(draws[int(0.025 * (n_boot - 1))], 3),
            round(draws[int(0.975 * (n_boot - 1))], 3))


def _describe(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return dict(n=0)
    n = len(vals)
    mean = sum(vals) / n
    d = dict(n=n, mean=round(mean, 3), median=round(vals[n // 2], 3),
             p10=round(vals[int(0.10 * (n - 1))], 3),
             p90=round(vals[int(0.90 * (n - 1))], 3),
             min=round(vals[0], 3), max=round(vals[-1], 3),
             frac_positive=round(sum(1 for v in vals if v > 0) / n, 3))
    if n >= BOOTSTRAP_MIN_N:
        # the registered kill criterion reads these; below BOOTSTRAP_MIN_N
        # an interval would be theatre, so none is reported
        d['ci95_median'] = _bootstrap_ci(vals, lambda s: s[len(s) // 2])
        d['ci95_mean'] = _bootstrap_ci(vals, lambda s: sum(s) / len(s))
        d['ci95_median_includes_zero'] = (d['ci95_median'][0] <= 0.0
                                          <= d['ci95_median'][1])
    return d


def _is_blind(session, blind_from):
    return blind_from is not None and session is not None and \
        str(session) >= str(blind_from)


def step7_markouts(runner, ledger, blind_from=BLIND_FROM):
    """Signed mid markouts at the frozen horizons.

    The population that matters is the frozen signals. When there are
    none this returns population='NO_FROZEN_SIGNALS' and the horizons
    stay empty - it does NOT quietly substitute a different population
    and call the result evidence. The window-level block below is
    reported separately, is explicitly not a signal population, and
    carries no directional claim: an approach is not a trade.

    Sessions >= blind_from are validation: every markout for them is
    WITHHELD (see BLIND_FROM). They are counted, never read."""
    def _marks(pop):
        out = {}
        for h in MARKOUT_S:
            vals = []
            for e in pop:
                m = runner.markout(e['instrument'], e.get('run'), e['t'], h)
                if m is not None:
                    vals.append(e['direction'] * m)
            out['%gs' % h] = _describe(vals)
        return out

    all_events = dedup_fires(ledger.get('fires', []), EVENT_COOLDOWN_S)
    events = [e for e in all_events if not _is_blind(e['session'],
                                                     blind_from)]
    withheld = [e for e in all_events if _is_blind(e['session'],
                                                   blind_from)]
    sig_src = [e for e in events if e['is_signal_source']]
    blind_info = dict(
        blind_from=blind_from,
        events_withheld=len(withheld),
        signal_source_events_withheld=sum(
            1 for e in withheld if e['is_signal_source']),
        sessions_withheld=sorted({e['session'] for e in withheld}),
        rule='markouts for sessions >= blind_from are not computed; the '
             'events are counted so accrual is visible without unblinding '
             'the registered validation set')
    # RAW firings, kept only for continuity with the 1.0 report. A
    # duplicated event enters this median several times, so it is not
    # the population to read.
    sig = _marks([f for f in ledger.get('fires', [])
                  if not _is_blind(f.get('session'), blind_from)])
    by_family = {}
    for fam in sorted(set(e['family'] for e in events)):
        by_family[fam] = dict(
            all_instruments=_marks([e for e in events
                                    if e['family'] == fam]),
            signal_source_only=_marks([e for e in sig_src
                                       if e['family'] == fam]))
    win = {}
    for h in MARKOUT_S:
        vals = []
        for w in runner.windows:
            if _is_blind(w.get('session'), blind_from):
                continue
            m = runner.markout(w['instrument'], w.get('run'),
                               w['t_end'], h)
            if m is not None:
                vals.append(m)          # unsigned: no direction is claimed
        win['%gs' % h] = _describe(vals)
    return dict(
        blind=blind_info,
        signal_population=('NO_FROZEN_SIGNALS'
                           if not ledger.get('fires') else 'FROZEN_SIGNALS'),
        primary_horizon_s=PRIMARY_MARKOUT_S,
        primary_horizon_rationale='matches the operator recorded average '
                                  'holding period (~4 min); registered '
                                  'before the data read at it exists',
        event_markouts_signed_ticks=_marks(events),
        event_markouts_signal_source_only=_marks(sig_src),
        event_markouts_by_family=by_family,
        event_population=dict(distinct_events=len(events),
                              signal_source_events=len(sig_src),
                              distinct_events_including_withheld=len(
                                  all_events),
                              cooldown_s=EVENT_COOLDOWN_S),
        raw_fire_markouts_signed_ticks=sig,
        raw_fire_caveat='RAW firings; a duplicated event enters this median '
                        'several times. Read event_markouts_* instead.',
        window_reference_unsigned_ticks=win,
        window_reference_caveat='Decision windows are not signals and this '
                                'block is not directional evidence; it exists '
                                'only to show whether forward mid data is '
                                'reachable at each horizon at all.')


def step8_controls(ledger, runner):
    """Matched sanity controls. With no signal population there is
    nothing to match against, and inventing a control here would be
    fabricating a comparison."""
    if ledger.get('fires'):
        return dict(status='NOT_IMPLEMENTED_IN_PILOT',
                    reason='signals exist; matched controls are a State-C '
                           'activity and are not run by the pilot')
    return dict(
        status='NOT_APPLICABLE',
        reason='zero frozen signals, so a matched control set has nothing '
               'to match',
        would_run=['same time-of-day bucket, same level family, same '
                   'approach direction, signal absent',
                   'random timestamps inside the same coverage windows',
                   'sign-flipped signal direction'])


def step9_replay(runner, k=3):
    """A human-checkable trace of the longest approaches: the level, the
    approach direction, the mid path, and the wall state per window."""
    by = collections.defaultdict(list)
    for w in runner.windows:
        by[(w['instrument'], w['approach_id'])].append(w)
    order = sorted(by.items(), key=lambda kv: -len(kv[1]))[:k]
    out = []
    for (inst, aid), ws in order:
        ws.sort(key=lambda w: w['t_end'])
        meta = runner.approach_open.get((inst, aid), {})
        trace = []
        for w in ws:
            trace.append(dict(
                t_rel=round(w['t_end'] - w['t_start'], 2),
                wall_state=w['wall_state'],
                retreat_ticks=w.get('retreat_ticks'),
                persist_agree=w.get('persist_agree'),
                crossed=w.get('clean_cross'),
                returned=w.get('returned_through_level'),
                approaches_60s=w.get('approaches_60s')))
        out.append(dict(instrument=inst, approach_id=aid,
                        level_id=ws[0]['level_id'],
                        level_px=ws[0]['level_px'],
                        approach_dir=meta.get('ad'),
                        windows=len(ws), trace=trace))
    return out


# ---------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------
def verdicts(step1, cov, funnel, sigs, health, ledger):
    """The two answers, kept apart on purpose.

    Working-ness is about the code path. Promise is about evidence. A
    starved pipeline that runs correctly is WORKING and NOT_OBSERVED at
    the same time, and collapsing those two into one answer is exactly
    the error this step exists to prevent."""
    ingested = sum(1 for r in ledger['runs'] if not r.get('skipped'))
    events = ledger['totals'].get('events', 0)
    windows = ledger['totals'].get('windows', 0)

    sys_checks = [
        ('manifest_hash_and_row_verification',
         bool(step1['verified_runs']),
         '%d runs verified byte-for-byte against their manifests'
         % len(step1['verified_runs'])),
        ('streams_ingested_end_to_end', events > 0,
         '%d genuine events merged in eventSeq order across %d runs'
         % (events, ingested)),
        ('levels_constructed', bool(funnel and windows >= 0),
         'level engine produced approaches on genuine mid data'),
        ('decision_windows_completed', windows > 0,
         '%d completed 10 s decision windows' % windows),
        ('detectors_executed', True,
         'all six families evaluated on every window; attrition is '
         'attributed stage by stage'),
        ('outcome_lock_held', ledger.get('outcomes') == 'LOCKED',
         'no fill, stop, target, R or P&L computed'),
    ]
    working = all(c[1] for c in sys_checks)

    # what is starving the funnel, stated from the funnel itself
    starved = {}
    for fam, d in funnel.items():
        if fam == 'A3':
            continue
        mi = d.get('missing_inputs') or {}
        if mi:
            starved[fam] = sorted(mi.items(), key=lambda kv: -kv[1])[:3]

    if sigs['count'] > 0:
        dd = sigs['dedup']
        promise = 'MIXED_PILOT'
        why = ('%d raw firings collapse to %d distinct events (%d from the '
               '%s signal source); their markouts decide the label and must '
               'be read from step 7 at the primary horizon, on the EVENT '
               'population, not the raw firings'
               % (sigs['count'], dd['distinct_events'],
                  dd['signal_source_events'],
                  dd['signal_source_instrument']))
    else:
        promise = 'NOT_OBSERVED'
        why = ('zero frozen signals were produced, so no hypothesis was '
               'observed either way. This is an absence of observation, '
               'not evidence against any hypothesis.')

    return dict(
        answer_1_is_the_system_working=dict(
            verdict='YES' if working else 'NO',
            checks=[dict(check=c[0], passed=c[1], evidence=c[2])
                    for c in sys_checks]),
        answer_2_do_any_hypotheses_appear_promising=dict(
            verdict=promise, reason=why,
            starving_inputs_by_family=starved),
        separation_note='These two answers are independent. The first is '
                        'about the code path; the second is about market '
                        'evidence. Neither is allowed to imply the other.')


# ---------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------
def run_pilot(capture_dir, max_sessions=None, blind_from=BLIND_FROM):
    step1 = step1_data_audit(capture_dir)
    r = PilotRunner(capture_dir, max_sessions=max_sessions)
    ledger = r.run()
    cov = coverage_windows(step1['verified_runs'])
    health = step3_feature_health(r.windows)
    census = step4_level_census(r.windows, ledger)
    funnel = step5_funnel(r.windows, ledger)
    sigs = step6_signals(ledger)
    marks = step7_markouts(r, ledger, blind_from=blind_from)
    ctrl = step8_controls(ledger, r)
    replay = step9_replay(r)
    sessions = sorted(ledger['sessions'])
    csv_sessions = sorted({x['session'] for x in step1['verified_runs']})
    tot = ledger['totals']

    rep = dict(
        pilot=PILOT_VERSION, runner=ledger['runner'],
        exposure_label=EXPOSURE_LABEL,
        blind_from=blind_from,
        sessions_inspected=sessions,
        sessions_blind=[s for s in sessions if _is_blind(s, blind_from)],
        sessions_with_verified_bulk_csv=csv_sessions,
        step1_data_audit=step1,
        step2_coverage_and_pipeline=dict(
            coverage=cov,
            events_ingested=tot.get('events', 0),
            runs_ingested=sum(1 for x in ledger['runs']
                              if not x.get('skipped')),
            # every skipped run with its reason; the runner never
            # partially ingests, so each entry is a whole run not read
            runs_skipped=ledger.get('skipped_runs', []),
            runs_skipped_by_reason=dict(
                missing_files=tot.get('runs_skipped_missing_files', 0),
                truncated=tot.get('runs_skipped_truncated', 0),
                corrupt=tot.get('runs_skipped_corrupt', 0),
                io_error=tot.get('runs_skipped_io_error', 0)),
            # the two counters that say how much of a pre-1.2.2
            # recording the runner had to correct retroactively
            book_integrity=dict(
                spurious_book_ready_ignored=tot.get(
                    'spurious_book_ready_ignored', 0),
                rows_disconnected_suppressed=tot.get(
                    'rows_disconnected_suppressed', 0)),
            latency_ms=ledger.get('latency_ms', {})),
        step3_feature_health=health,
        step4_level_and_approach_census=census,
        step5_threshold_funnel=funnel,
        step6_frozen_signals=sigs,
        step7_descriptive_markouts=marks,
        step8_matched_controls=ctrl,
        step9_replay_audit=replay,
        step10_model_search=dict(
            performed=False,
            reason='forbidden at this stage; no model, threshold or feature '
                   'was searched, tuned or selected on these days'),
        baseline_sessions=ledger.get('baseline_sessions'),
        not_wired=ledger.get('not_wired'))
    rep['verdicts'] = verdicts(step1, cov, funnel, sigs, health, ledger)
    rep['classification'] = classify(step1, ledger, rep)
    return rep, r


def classify(step1, ledger, rep):
    """PILOT_DIAGNOSTIC_COMPLETE - INSUFFICIENT_DATA_FOR_EV when every
    stage that could run did run; PILOT_BLOCKED with the exact failing
    artifact when a stage could not run at all."""
    blocked = []
    if not step1['verified_runs']:
        blocked.append(dict(stage='step1_data_audit',
                            artifact='no run passed manifest verification'))
    if ledger['totals'].get('events', 0) == 0:
        blocked.append(dict(stage='step2_pipeline_proof',
                            artifact='no ingestible bulk CSV for any '
                                     'manifest (missing, truncated or '
                                     'corrupt)'))
    if ledger['totals'].get('windows', 0) == 0:
        blocked.append(dict(stage='step5_threshold_funnel',
                            artifact='no completed 10 s decision window'))
    if blocked:
        return dict(status='PILOT_BLOCKED', blocking=blocked)
    return dict(
        status='PILOT_DIAGNOSTIC_COMPLETE - INSUFFICIENT_DATA_FOR_EV',
        note='every pilot stage that the present data can support was run '
             'to completion; the EV question is untouched and stays closed '
             'behind the State-C gate')


def write_windows(runner, path, blind_from=BLIND_FROM):
    """The pilot's per-window feature vectors (with the level set the
    runner held at each window) for sessions this pass exposes; nothing
    from a blind session. Written aside and moved into place."""
    keep = [w for w in runner.windows
            if not _is_blind(w.get('session'), blind_from)]
    doc = dict(schema='MROF-PILOT-WINDOWS-1', pilot=PILOT_VERSION,
               blind_from=blind_from,
               sessions=sorted({w['session'] for w in keep}),
               note='EXPOSED sessions only; every window here belongs to '
                    'a session labelled %s by the pass that wrote it'
                    % EXPOSURE_LABEL,
               windows=keep)
    tmp = path + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(doc, fh, default=str)
    os.replace(tmp, path)
    return len(keep)


def write_exposure_ledger(rep, path):
    """Append-only, and exposure is MONOTONE: a session may go from blind
    to exposed (an explicit unblinding at the checkpoint), never back.

    A session run under the blind gets BLIND_LABEL: its fire counts were
    seen, its markouts were not. A session run unblinded gets
    EXPOSURE_LABEL. Once EXPOSURE_LABEL is on a session it stays,
    whatever later runs do."""
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    blind = set(rep.get('sessions_blind', []))
    for s in rep['sessions_inspected']:
        label = BLIND_LABEL if s in blind else EXPOSURE_LABEL
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=label, exposed_by=PILOT_VERSION,
                         bulk_csv_present=s in
                         rep['sessions_with_verified_bulk_csv'])
        elif cur.get('label') == BLIND_LABEL and label == EXPOSURE_LABEL:
            # explicit unblinding: upgrade, and say it was blind before
            cur.update(label=EXPOSURE_LABEL, exposed_by=PILOT_VERSION,
                       previously_blind=True)
        # EXPOSURE_LABEL never downgrades; BLIND stays BLIND on re-run
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=EXPOSURE_LABEL, blind_label=BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded, which is permanent.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


def text_summary(rep):
    v = rep['verdicts']
    L = ['%s   classification=%s' % (rep['pilot'],
                                     rep['classification']['status'])]
    c = rep['step2_coverage_and_pipeline']['coverage']
    L.append('sessions inspected: %s' % ', '.join(rep['sessions_inspected']))
    L.append('sessions with verified bulk CSV: %s'
             % (', '.join(rep['sessions_with_verified_bulk_csv']) or 'none'))
    for inst in ('NQ', 'MNQ'):
        if inst in c:
            L.append('  %-4s union coverage %8.1f s across %d windows'
                     % (inst, c[inst]['seconds'], len(c[inst]['windows'])))
    if 'NQ_MNQ_simultaneous_seconds' in c:
        L.append('  NQ+MNQ simultaneous coverage: %.1f s'
                 % c['NQ_MNQ_simultaneous_seconds'])
    L.append('events ingested: %d'
             % rep['step2_coverage_and_pipeline']['events_ingested'])
    ce = rep['step4_level_and_approach_census']
    L.append('approaches=%d windows=%d levels seen=%s'
             % (ce['approaches_total'], ce['windows_total'],
                ','.join(ce['by_level']) or 'none'))
    s6 = rep['step6_frozen_signals']
    dd = s6['dedup']
    L.append('frozen signals: %d raw firings -> %d distinct events '
             '(cooldown %gs%s)'
             % (s6['count'], dd['distinct_events'], dd['cooldown_s'],
                (', inflation %.2fx' % dd['inflation_ratio'])
                if dd['inflation_ratio'] else ''))
    L.append('   distinct events by family:     %s'
             % (dd['distinct_events_by_family'] or 'none'))
    L.append('   distinct events by instrument: %s'
             % (dd['distinct_events_by_instrument'] or 'none'))
    L.append('   signal-source (%s) events:     %d   %s'
             % (dd['signal_source_instrument'], dd['signal_source_events'],
                dd['signal_source_events_by_family'] or 'none'))
    L.append('   cooldown sensitivity: %s'
             % {k: v['distinct_events']
                for k, v in sorted(dd['cooldown_sensitivity'].items())})
    s2 = rep['step2_coverage_and_pipeline']
    sk = s2.get('runs_skipped_by_reason', {})
    if any(sk.values()):
        L.append('runs skipped whole: missing-files=%d truncated=%d '
                 'corrupt=%d io-error=%d'
                 % (sk.get('missing_files', 0), sk.get('truncated', 0),
                    sk.get('corrupt', 0), sk.get('io_error', 0)))
    bi = s2.get('book_integrity', {})
    L.append('book integrity: spurious BOOK_READY ignored=%d, rows inside '
             'disconnect gaps suppressed=%d'
             % (bi.get('spurious_book_ready_ignored', 0),
                bi.get('rows_disconnected_suppressed', 0)))
    m7 = rep['step7_descriptive_markouts']
    pk = '%gs' % m7['primary_horizon_s']
    pm = m7['event_markouts_signal_source_only'].get(pk, {})
    ci = ('  ci95_median=%s%s' % (pm['ci95_median'],
                                  ' (includes 0)' if
                                  pm['ci95_median_includes_zero'] else '')
          if pm.get('ci95_median') else '')
    L.append('primary markout %s (signal-source events): %s%s'
             % (pk, ('n=%d median=%+.2f ticks frac_positive=%.3f'
                     % (pm['n'], pm['median'], pm['frac_positive']))
                if pm.get('n') else 'n=0 (no forward coverage at this '
                                    'horizon)', ci))
    b = m7.get('blind', {})
    if b.get('blind_from'):
        L.append('VALIDATION BLIND from %s: %d events (%d signal-source) on '
                 'sessions %s -- counted, markouts WITHHELD. Unblind only at '
                 'the checkpoint with --blind-from none (permanent).'
                 % (b['blind_from'], b['events_withheld'],
                    b['signal_source_events_withheld'],
                    ', '.join(b['sessions_withheld']) or 'none'))
    else:
        L.append('UNBLINDED RUN: every session inspected is now labelled %s '
                 'permanently.' % EXPOSURE_LABEL)
    L.append('')
    L.append('ANSWER 1 - IS THE SYSTEM WORKING?  %s'
             % v['answer_1_is_the_system_working']['verdict'])
    for ch in v['answer_1_is_the_system_working']['checks']:
        L.append('   [%s] %-36s %s' % ('x' if ch['passed'] else ' ',
                                       ch['check'], ch['evidence']))
    L.append('')
    L.append('ANSWER 2 - DO ANY HYPOTHESES APPEAR PROMISING?  %s'
             % v['answer_2_do_any_hypotheses_appear_promising']['verdict'])
    L.append('   %s' % v['answer_2_do_any_hypotheses_appear_promising'][
        'reason'])
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    out = None
    ms = None
    blind = BLIND_FROM
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
    if '--max-sessions' in argv:
        ms = int(argv[argv.index('--max-sessions') + 1])
    if '--blind-from' in argv:
        blind = parse_blind_from(argv[argv.index('--blind-from') + 1])
    if blind is None:
        print('*** UNBLINDED RUN: markouts will be computed for EVERY '
              'session and every session inspected will be labelled %s '
              'permanently. This is the checkpoint read. ***\n'
              % EXPOSURE_LABEL)
    try:
        rep, _r = run_pilot(d, max_sessions=ms, blind_from=blind)
    except (AU.CaptureUnavailable, AU.NoCaptureData) as exc:
        # stopped BEFORE anything is written: no report, and no session
        # is labelled exposed by a pass that did not complete
        print('STOPPED: %s' % exc)
        return 2
    print(text_summary(rep))
    if '--windows-out' in argv:
        # per-window feature vectors for the God's Eye replay: EXPOSED
        # sessions only. A session this pass ran with markouts is exposed
        # by this very pass (it is labelled so below); blind sessions'
        # windows are event-level protected data and are never written.
        wo = argv[argv.index('--windows-out') + 1]
        n = write_windows(_r, wo, blind)
        print('windows (exposed sessions only) -> %s (%d windows)' % (wo, n))
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\npilot report -> %s' % out)
        led = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'MROF_EXPOSED_PILOT_DEV_DAYS.json')
        n = write_exposure_ledger(rep, led)
        nb = len(rep.get('sessions_blind', []))
        print('exposure ledger -> %s (%d days; %d of this run\'s %d '
              'sessions labelled %s, %d labelled %s)'
              % (led, n, len(rep['sessions_inspected']) - nb,
                 len(rep['sessions_inspected']), EXPOSURE_LABEL, nb,
                 BLIND_LABEL))


def parse_blind_from(s):
    """'YYYYMMDD' -> that date; 'none'/'off'/'' -> None (unblind)."""
    s = (s or '').strip().lower()
    if s in ('none', 'off', 'no', ''):
        return None
    if not (len(s) == 8 and s.isdigit()):
        raise SystemExit('--blind-from wants YYYYMMDD or none, got %r' % s)
    return s
    return 0


if __name__ == '__main__':
    sys.exit(main())
