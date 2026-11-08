#!/usr/bin/env python3
"""mrofyt_cpcompare.py - MROF-YT-CPCOMPARE-1.0

Compares the NQ results of two checkpoint reports, value by value: every
test, trade count, win rate, net result, interval, verdict, the
scorecard and the headline. Made to prove a faster read on DEV before it
is used on held-out sessions: the full DEV report against the same DEV
run read with --nq-only (or under another Python, such as PyPy). Every
NQ number must agree.

Left out of the comparison, because they differ by design between a
full and an NQ-only read: everything MNQ's (keys naming MNQ, rows whose
instrument is MNQ), and the bookkeeping that counts both instruments
together (the runner's ledger, the session lists, wave eighteen's count
of trades without a recent range, the checkpoint's version and the
instruments it read). A difference in the sessions read is shown as a
note, never hidden.

    python3 mrofyt_cpcompare.py cp_dev.json cp_dev_fast.json

Exit 0: MATCH. Exit 1: DIFFERENT (each differing value named). Exit 2: a
file cannot be read, is not a checkpoint report, or the two reports are
not the same kind of read (DEV, unblind, holdout).

Reads two report files; reads no recording, writes nothing. No order is
placed.
"""

import json
import numbers
import sys

CPCOMPARE_VERSION = 'MROF-YT-CPCOMPARE-1.0'
OTHER = 'MNQ'
BOOKKEEPING = frozenset((
    'checkpoint', 'instruments', 'runner', 'sessions_inspected',
    'sessions_refused', 'sessions_evaluated', 'no_recent_range'))
REL_TOL = 1e-9


def nq_view(x):
    """The report with everything MNQ's and the shared bookkeeping
    removed, at every depth."""
    if isinstance(x, dict):
        return {k: nq_view(v) for k, v in x.items()
                if not str(k).startswith(OTHER) and k not in BOOKKEEPING}
    if isinstance(x, (list, tuple)):
        return [nq_view(v) for v in x
                if not (isinstance(v, dict) and v.get('instrument') == OTHER)]
    return x


def _same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, numbers.Real) and isinstance(b, numbers.Real):
        return a == b or abs(a - b) <= REL_TOL * max(1.0, abs(a), abs(b))
    return a == b


def differences(a, b, path=''):
    """[(path, value in a, value in b)] of every value that differs, and
    the number of values compared."""
    out, n = [], 0
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = '%s/%s' % (path, k) if path else str(k)
            if k not in a or k not in b:
                out.append((p, a.get(k, '<missing>'), b.get(k, '<missing>')))
                continue
            d, m = differences(a[k], b[k], p)
            out += d
            n += m
        return out, n
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [(path + ' (length)', len(a), len(b))], 1
        for i, (x, y) in enumerate(zip(a, b)):
            d, m = differences(x, y, '%s[%d]' % (path, i))
            out += d
            n += m
        return out, n
    return ([] if _same(a, b) else [(path, a, b)]), 1


def compare(rep_a, rep_b):
    """dict(match, compared, diffs=[(path, a, b)], notes=[...])."""
    for rep in (rep_a, rep_b):
        if not (isinstance(rep, dict) and 'reports' in rep and
                'summary' in rep and 'checkpoint' in rep):
            raise ValueError('not a checkpoint report (no reports, summary '
                             'or checkpoint version in it)')
    if rep_a.get('mode') != rep_b.get('mode'):
        raise ValueError('not the same kind of read: %s against %s'
                         % (rep_a.get('mode'), rep_b.get('mode')))
    diffs, n = differences(nq_view(rep_a), nq_view(rep_b))
    notes = []
    sa = set(rep_a.get('sessions_inspected') or ())
    sb = set(rep_b.get('sessions_inspected') or ())
    if sa != sb:
        notes.append('sessions read differ (expected only where one '
                      'instrument recorded a day the other did not): only '
                      'in the first %s; only in the second %s'
                      % (sorted(sa - sb) or '-', sorted(sb - sa) or '-'))
    for rep, which in ((rep_a, 'first'), (rep_b, 'second')):
        notes.append('%s: %s, instruments read %s' % (
            which, rep.get('checkpoint'),
            ', '.join(rep.get('instruments') or ['NQ', 'MNQ'])))
    return dict(match=not diffs, compared=n, diffs=diffs, notes=notes)


def text(res, a='first', b='second', limit=40):
    lines = []
    if res['match']:
        lines.append('MATCH: every NQ value agrees (%d values compared).'
                     % res['compared'])
    else:
        lines.append('DIFFERENT: %d of %d NQ values differ.'
                     % (len(res['diffs']), res['compared']))
        for p, x, y in res['diffs'][:limit]:
            lines.append('  %s\n      %s: %s\n      %s: %s'
                         % (p, a, str(x)[:200], b, str(y)[:200]))
        if len(res['diffs']) > limit:
            lines.append('  ... and %d more' % (len(res['diffs']) - limit))
    for x in res['notes']:
        lines.append('note: %s' % x)
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    reps = []
    for p in argv:
        try:
            with open(p) as fh:
                reps.append(json.load(fh))
        except (OSError, ValueError) as exc:
            print('STOPPED: cannot read %s (%s)' % (p, exc))
            return 2
    try:
        res = compare(reps[0], reps[1])
    except ValueError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print('%s\n  first:  %s\n  second: %s\n' % (CPCOMPARE_VERSION, argv[0],
                                               argv[1]))
    print(text(res, argv[0], argv[1]))
    return 0 if res['match'] else 1


if __name__ == '__main__':
    sys.exit(main())
