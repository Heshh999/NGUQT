#!/usr/bin/env python3
"""mrofyt_checkpoint.py - MROF-YT-CHECKPOINT-1.0

Every registered test that reads the recordings, in ONE pass. The
recordings are read once by the last runner of the chain (wave
thirteen's, which carries every wave's hooks); each wave's own,
unchanged report code then runs on that same finished read, so every
test is scored exactly as its own command would score it. Nothing is
added, merged or re-tuned: each wave keeps its own registration,
verdicts and withholding.

    wave 6    L2's stops, L4, trapped volume          (frozen DEV cut)
    wave 8    L2 first touch, morning, both, 5 min
    wave 9    L2 next-level and scaled targets        (needs --a-ref)
    wave 10   candle-close break and reclaim
    wave 11   early entry; swings, opens, VWAP, pivots (wick, early, close)
    wave 12   trend-day and big-day filters           (2026 calendar)
    wave 13   back into yesterday's value area
    wave 14   L2 at the first signal of each level    THE HEADLINE TEST
    wave 15   initial balance, round 100s, equal highs and lows
    16A       does the order flow add to the levels?
    16B       limit entry against market entry
    wave 17   confluence grades A+ / A / B over every level family; sizing

Not here: wave seven (its own engine; refresh its DEV cuts first), and
the minute-export parts 16A-history and 16C (other data).

    python3 mrofyt_checkpoint.py "<capture>" --a-ref w9_frozen.json --out cp_dev.json
    python3 mrofyt_checkpoint.py "<old>;<new>" --unblind --a-ref w9_frozen.json --out cp_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import json
import os
import sys

import mrofyt_closereclaim as C
import mrofyt_confluence as CF
import mrofyt_earlylevels as E
import mrofyt_l2context as X
import mrofyt_l2firstsignal as FS
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_limitentry as LE
import mrofyt_minutelevels as ML
import mrofyt_obviouslevels as OL
import mrofyt_runner as RUN
import mrofyt_valuearea as VA

CHECKPOINT_VERSION = 'MROF-YT-CHECKPOINT-1.0'
HERE = os.path.dirname(os.path.abspath(__file__))
W6_FROZEN = os.path.join(HERE, 'frozen_dev_20261031', 'w6_frozen.json')
CALENDAR = os.path.join(HERE, 'calendar_2026_events.csv')
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
HEADLINE = 'wave 14'


def _plan(w6_frozen, w9_frozen, calendar):
    """[(label, module, runner class name, version, call, text)] in wave
    order; call(d, unblind, holdout, ms) -> (rep, runner)."""
    a_ref = (w9_frozen or {}).get('a_ref')
    plan = [
        ('wave 6', LB, 'LevelBreakRunner', LB.W6_VERSION,
         lambda d, u, h, m: LB.run_evaluate(d, w6_frozen, u, h, m), LB.text),
        ('wave 8', V, 'L2VariantRunner', V.W8_VERSION,
         lambda d, u, h, m: V.run(d, u, h, m), V.text)]
    if w9_frozen is not None:
        plan.append(('wave 9', W, 'TargetRunner', W.W9_VERSION,
                     lambda d, u, h, m: W.run_evaluate(d, w9_frozen, u, h, m),
                     W.text))
    plan += [
        ('wave 10', C, 'CloseRunner', C.W10_VERSION,
         lambda d, u, h, m: C.run(d, u, h, m), C.text),
        ('wave 11', E, 'LevelsRunner', E.W11_VERSION,
         lambda d, u, h, m: E.run(d, u, h, a_ref, m), E.text),
        ('wave 12', X, 'ContextRunner', X.W12_VERSION,
         lambda d, u, h, m: X.run(d, u, h, calendar, m), X.text),
        ('wave 13', VA, 'ValueRunner', VA.W13_VERSION,
         lambda d, u, h, m: VA.run(d, u, h, a_ref, m), VA.text),
        ('wave 14', FS, 'FirstSignalRunner', FS.W14_VERSION,
         lambda d, u, h, m: FS.run(d, u, h, m), FS.text),
        ('wave 15', OL, 'ObviousLevelsRunner', OL.W15_VERSION,
         lambda d, u, h, m: OL.run(d, u, h, m), OL.text),
        ('16A', ML, 'MinuteLevelsRunner', ML.W16A_VERSION,
         lambda d, u, h, m: ML.run_recordings(d, u, h, m),
         ML.text_recordings),
        ('16B', LE, 'LimitRunner', LE.W16B_VERSION,
         lambda d, u, h, m: LE.run(d, u, h, m), LE.text),
        ('wave 17', CF, 'ConfluenceRunner', CF.W17_VERSION,
         lambda d, u, h, m: CF.run(d, u, h, m), CF.text)]
    return plan


def scorecard(rep):
    """[(where, test, n, status)] of every NQ row in one wave's report
    that carries a status (references and descriptions included)."""
    out = []

    def walk(x, path):
        if isinstance(x, dict):
            if 'status' in x and ('n' in x or 'trades' in x):
                name = x.get('test') or x.get('name') or '/'.join(path[-2:])
                out.append(('/'.join(path), str(name),
                            x.get('n', x.get('trades')), x['status']))
                return
            for k, v in x.items():
                if k == 'MNQ':
                    continue
                walk(v, path + [str(k)])
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, path + [str(i)])
    for key in ('tests', 'results', 'tables', 'groups'):
        if key in rep:
            walk(rep[key], [key])
    return out


def is_test(status):
    s = str(status)
    return not (s.startswith('REFERENCE') or s.startswith('DESCRIBED') or
                s == 'withheld')


def run(capture_dir, unblind=False, holdout=False, w6_frozen=None,
        w9_frozen=None, calendar=None, max_sessions=None):
    """One read, every wave's report on it: {label: rep}, the runner."""
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = VA.ValueRunner(capture_dir, unblind=unblind, holdout=holdout,
                       max_sessions=max_sessions)
    led = r.run()
    r.run = lambda: led                      # every wave reuses this read
    reports, texts = {}, {}
    for label, mod, cls, _ver, call, txt in _plan(w6_frozen, w9_frozen,
                                                 calendar):
        real = getattr(mod, cls)
        setattr(mod, cls, lambda *a, **k: r)
        try:
            rep, _r = call(capture_dir, unblind, holdout, max_sessions)
        finally:
            setattr(mod, cls, real)
        reports[label] = rep
        texts[label] = txt(rep)
    rows = {label: scorecard(rep) for label, rep in reports.items()}
    head = reports[HEADLINE]['results'][FS.PRIMARY]['test']
    summary = dict(
        headline=dict(test='wave 14: L2 at the first signal of each level',
                      n=head['n'], status=head['status']),
        tests=sum(1 for v in rows.values() for x in v if is_test(x[3])),
        passing=[(lab, x[1], x[2], x[3]) for lab, v in rows.items()
                 for x in v if is_test(x[3]) and
                 str(x[3]).split(' ')[0] in ('PASS', 'PROMISING')])
    rep = dict(checkpoint=CHECKPOINT_VERSION,
               mode='unblind' if unblind else ('holdout' if holdout
                                               else 'dev'),
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               waves=[lab for lab in reports],
               not_run=[x for x in (
                   None if w9_frozen is not None else
                   'wave 9: needs its frozen DEV file (--a-ref '
                   'w9_frozen.json)',
                   'wave 7: its own engine; refresh its DEV cuts, then run '
                   'mrofyt_flowlevels.py',
                   '16A history and 16C: NQ minute exports, their own '
                   'commands') if x],
               summary=summary, scorecard=rows, reports=reports)
    return rep, texts, r


def text(rep, texts):
    s = rep['summary']
    lines = ['%s  %s  (one read, every recordings test)'
             % (rep['checkpoint'], rep['mode']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             '',
             'HEADLINE  %s: %d trades -> %s' % (
                 s['headline']['test'], s['headline']['n'],
                 s['headline']['status']),
             '',
             'SCORECARD (NQ; every test row of every wave; references and '
             'descriptions marked)']
    for lab, rows in rep['scorecard'].items():
        for where, name, n, status in rows:
            lines.append('  %-8s %-34s %5s  %s' % (
                lab, name[:34], '-' if n is None else n, status))
    lines.append('')
    lines.append('%d tests in this read; passing: %s' % (
        s['tests'], ', '.join('%s %s' % (a, b) for a, b, _n, _s in
                              s['passing']) or 'none'))
    lines.append('With this many tests a pass or two can come from luck: a '
                 'pass outside the headline is promising, to be confirmed '
                 'on later sessions, not proven.')
    for x in rep['not_run']:
        lines.append('NOT IN THIS READ: %s' % x)
    for lab in rep['waves']:
        lines.append('')
        lines.append('=' * 72)
        lines.append(lab.upper())
        lines.append('=' * 72)
        lines.append(texts[lab])
    return '\n'.join(lines)


def _load(path, what):
    try:
        return json.load(open(path))
    except (OSError, ValueError) as exc:
        raise ValueError('%s: cannot read %s (%s)' % (what, path, exc))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    try:
        w6 = _load(arg('--w6') or W6_FROZEN, 'wave six\'s frozen cut')
        if 'trapped_cut' not in w6:
            raise ValueError('wave six\'s frozen cut: no trapped_cut in it')
        w9 = None
        if arg('--a-ref'):
            w9 = _load(arg('--a-ref'), 'wave nine\'s frozen file')
            if not isinstance(w9.get('a_ref'), dict):
                raise ValueError('%s is not wave nine\'s frozen file (the '
                                 '--frozen-out of its DEV run)'
                                 % arg('--a-ref'))
        cal = X.read_calendar(arg('--calendar') or CALENDAR)
    except ValueError as exc:
        print('STOPPED: %s' % exc)
        return 2
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    if unblind or holdout:
        print('*** %s: every registered recordings test, once, in one '
              'read. ***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, texts, _r = run(argv[0], unblind, holdout, w6, w9, cal, ms)
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep, texts))
    out = arg('--out')
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\ncheckpoint report -> %s' % out)
    versions = [ver for lab, _m, _c, ver, _f, _t in _plan(w6, w9, cal)]
    if holdout:
        p = os.path.join(HERE, HOLDOUT_LEDGER)
        for ver in versions:
            n = LG.record_holdout_read(rep, p, ver)
        print('replay holdout read recorded for %d waves (%d read(s))'
              % (len(versions), n))
    if unblind:
        p = os.path.join(HERE, EXPOSURE_LEDGER)
        for ver in versions + [CHECKPOINT_VERSION]:
            n = LG.record_exposure(rep, p, ver)
        print('exposure ledger -> %d days, read by %d waves'
              % (n, len(versions)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
