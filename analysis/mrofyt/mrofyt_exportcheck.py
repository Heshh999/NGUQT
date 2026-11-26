#!/usr/bin/env python3
"""mrofyt_exportcheck.py - MROF-YT-EXPORTCHECK-1.0

Is a folder of one-minute exports fit to be read? A check of the DATA,
made before any rule is run on it. No return, level, signal or result
is computed, and no price is printed.

    the export   which contracts are there, how many bars, whether the
                 trading days run on without a hole, whether the export
                 script (src/MrofBarExport.cs) finished and what it said
                 of each contract
    against a    bar for bar, before the minute reader's gate
    reference    (2026-07-01): the same time stamps, the same open,
                 high, low, close and volume. The reference is a folder
                 of the Historical Data window's own exports. This is
                 the real test of the export script: NQ, written by the
                 script, against the NQ files exported by hand.

    python mrofyt_exportcheck.py "<export folder>" --market NQ
    python mrofyt_exportcheck.py "<export folder>" --market NQ
        --reference "<folder of manual exports>" [--out check.json]

Bars from the gate on are counted and never compared or shown.
Read-only; no order is placed.
"""
import collections
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402

EC_VERSION = 'MROF-YT-EXPORTCHECK-1.0'
SCRIPT_VERSION = 'MROF-BAR-EXPORT-1.0'
DAY_BARS = 300                 # a trading day, in one contract
MAX_GAP_DAYS = 5               # a long weekend is 4 calendar days
TOL = 1e-9                     # relative, on prices
SHIFTS = tuple(60 * k for k in range(-12, 13) if k) + (-1, 1)   # minutes
SHIFT_SHARE = 0.9
DIAGNOSE = 3                   # contracts a difference is looked into
SHOW = 5
END_DAYS = 7                   # the bars end this close to the export


class ExportCheckError(Exception):
    """A stop: nothing was judged."""


# ---------------------------------------------------------------------
# the files of one market
# ---------------------------------------------------------------------
def contract_key(contract):
    mm, yy = contract.split()[1].split('-')
    return yy, mm


def files_of(folder, root):
    """{contract: path} of the root's minute exports in a folder."""
    if not os.path.isdir(folder):
        raise ExportCheckError('%s is not a folder' % folder)
    held = collections.defaultdict(list)
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if not os.path.isfile(full) or '.Bid.' in name or '.Ask.' in name:
            continue
        c = CX.contract_of(name, root)
        if c is None or c.endswith(' CONT'):
            continue
        held[c].append(full)
    twice = sorted(c for c, v in held.items() if len(v) > 1)
    if twice:
        raise ExportCheckError(
            'more than one file holds the same contract (%s); keep one '
            'file per contract' % ', '.join(twice))
    if not held:
        raise ExportCheckError(
            'no %s minute exports in %s (expected files named like '
            '"%s 12-26.Last.txt")' % (root, folder, root))
    return {c: v[0] for c, v in held.items()}


def roots_in(folder):
    """The roots that have contract files in a folder, most files
    first."""
    n = collections.Counter()
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            m = CX._CONTRACT.match(name) or CX._CONTRACT_MON.match(name)
            if m and '.Bid.' not in name and '.Ask.' not in name:
                n[m.group('root')] += 1
    return [r for r, _k in n.most_common()]


def read_summary(folder, root):
    """What the export script wrote last, or None without it:
    dict(version, complete, rows={contract: (status, bars, why)})."""
    path = os.path.join(folder, 'MROF_EXPORT_%s.txt' % root)
    if not os.path.isfile(path):
        return None
    out = dict(version=None, complete=False, rows={}, market=None,
               time_zone=None, written=None, merge_policy=None,
               lookup_policy=None)
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if lines:
        out['version'] = lines[0]
    for ln in lines[1:]:
        p = ln.split(';')
        if p[0] == 'complete':
            out['complete'] = True
        elif p[0] == 'market' and len(p) > 1:
            out['market'] = p[1]
        elif p[0] == 'time_zone' and len(p) > 1:
            out['time_zone'] = p[1]
        elif p[0] == 'written_utc' and len(p) > 1:
            out['written'] = p[1][:8]
        elif p[0] in ('merge_policy', 'lookup_policy') and len(p) > 1:
            out[p[0]] = p[1]
        elif p[0] == 'contract' and len(p) >= 4:
            try:
                bars = int(p[3])
            except ValueError:
                bars = 0
            out['rows'][p[1]] = (p[2], bars, p[6] if len(p) > 6 else '')
    return out


# ---------------------------------------------------------------------
# reading one file
# ---------------------------------------------------------------------
_LINE = re.compile(r'^(\d{8}) (\d{6})[;,]([^;,]+)[;,]([^;,]+)[;,]([^;,]+)'
                   r'[;,]([^;,]+)[;,]([^;,]+)$')


_DAY0 = {}


def _minute(ymd, hms):
    """Minutes since 2000-01-01 of a stamp, as written."""
    d0 = _DAY0.get(ymd)
    if d0 is None:
        d0 = _DAY0[ymd] = (datetime.date(
            int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])).toordinal() -
            730120) * 1440
    return d0 + int(hms[:2]) * 60 + int(hms[2:4])


def _stamp(minute):
    d = datetime.date.fromordinal(730120 + minute // 1440)
    m = minute % 1440
    return '%04d%02d%02d %02d%02d00' % (d.year, d.month, d.day, m // 60,
                                         m % 60)


def load(path):
    """One contract file: dict(bars={minute: (o, h, l, c, v)} of the
    sessions before the gate, later=bars from the gate on (counted,
    not kept), sessions={session: bars}, bad, repeated, unordered,
    seconds=stamps that are not on a whole minute)."""
    bars, sessions = {}, collections.Counter()
    bad = repeated = unordered = later = seconds = 0
    last = None
    ses_of = {}
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            m = _LINE.match(line)
            if not m:
                bad += 1
                continue
            ymd, hms = m.group(1), m.group(2)
            try:
                o, h, lo, c, v = (float(m.group(k)) for k in range(3, 8))
                minute = _minute(ymd, hms)
            except ValueError:
                bad += 1
                continue
            if hms[4:] != '00':
                seconds += 1
            if last is not None and minute < last:
                unordered += 1
            last = minute
            key = (ymd, hms[:2])
            ses = ses_of.get(key)
            if ses is None or hms[2:4] in ('00', '01'):
                ses = CX.bar_session(ymd, hms)[0]
                if hms[2:4] not in ('00', '01'):
                    ses_of[key] = ses
            sessions[ses] += 1
            if ses >= CX.REFUSE_FROM:
                later += 1
                continue
            if minute in bars:
                repeated += 1
            bars[minute] = (o, h, lo, c, v)
    return dict(bars=bars, later=later, sessions=dict(sessions), bad=bad,
                repeated=repeated, unordered=unordered, seconds=seconds)


def same_bar(a, b):
    return all(abs(x - y) <= TOL * max(1.0, abs(x), abs(y))
               for x, y in zip(a, b))


# ---------------------------------------------------------------------
# the export on its own
# ---------------------------------------------------------------------
def _date(session):
    return datetime.date(int(session[:4]), int(session[4:6]),
                         int(session[6:8]))


def holes(days):
    """[(day before, day after, calendar days apart)] where two
    following trading days are more than MAX_GAP_DAYS apart."""
    out = []
    for a, b in zip(days, days[1:]):
        gap = (_date(b) - _date(a)).days
        if gap > MAX_GAP_DAYS:
            out.append((a, b, gap))
    return out


def describe(loaded):
    """loaded: {contract: load()}. The contracts, the trading days (a
    weekday with DAY_BARS bars or more in one contract) and their
    holes; nothing of any price."""
    rows = []
    full = collections.Counter()
    for c in sorted(loaded, key=contract_key):
        d = loaded[c]
        ses = sorted(s for s, n in d['sessions'].items() if n >= DAY_BARS
                     and _date(s).weekday() < 5)
        for s in ses:
            full[s] += 1
        every = sorted(d['sessions'])
        rows.append(dict(
            contract=c, bars=sum(d['sessions'].values()),
            bars_from_gate=d['later'], days=len(ses),
            first=every[0] if every else None,
            last=every[-1] if every else None, bad_lines=d['bad'],
            repeated=d['repeated'], unordered=d['unordered'],
            off_minute=d['seconds']))
    days = sorted(full)
    before = [s for s in days if s < CX.REFUSE_FROM]
    return dict(
        contracts=rows, trading_days=len(days),
        first_day=days[0] if days else None,
        last_day=days[-1] if days else None,
        days_before_gate=len(before), days_from_gate=len(days) - len(before),
        holes=[list(h) for h in holes(days)],
        days_in_two_contracts=sum(1 for s in days if full[s] > 1))


def export_verdict(desc, summary):
    """('COMPLETE' | 'INCOMPLETE', [why])."""
    why = []
    if desc['trading_days'] == 0:
        why.append('no trading day has %d bars' % DAY_BARS)
    for a, b, gap in desc['holes']:
        why.append('no trading day between %s and %s (%d days)' % (a, b,
                                                                    gap))
    for r in desc['contracts']:
        for k, text in (('bad_lines', 'lines that are not bars'),
                        ('repeated', 'time stamps written twice'),
                        ('unordered', 'bars out of time order'),
                        ('off_minute', 'stamps not on a whole minute')):
            if r[k]:
                why.append('%s: %d %s' % (r['contract'], r[k], text))
    if summary is not None:
        if summary['version'] != SCRIPT_VERSION:
            why.append('the summary is of %s, not %s' % (summary['version'],
                                                         SCRIPT_VERSION))
        if not summary['complete']:
            why.append('the export script did not finish')
        if summary['merge_policy'] == 'NOT SET':
            why.append('the script could not ask for each contract on its '
                       'own; it wrote no bars')
        if summary['lookup_policy'] == 'NOT SET':
            why.append('the script could not ask the data feed: only bars '
                       'already on the computer were written')
        w, last_day = summary['written'], desc['last_day']
        if w and last_day and len(w) == 8 and w.isdigit() and \
                (_date(w) - _date(last_day)).days > END_DAYS:
            why.append('the bars end on %s, %d days before the export was '
                       'made (%s): the newest contract is missing'
                       % (last_day, (_date(w) - _date(last_day)).days, w))
        with_bars = [c for c, (st, _n, _w) in summary['rows'].items()
                     if st == 'OK']
        last = max(with_bars, key=contract_key) if with_bars else None
        on_disk = {r['contract']: r['bars'] for r in desc['contracts']}
        for c in sorted(summary['rows'], key=contract_key):
            st, n, w = summary['rows'][c]
            if st == 'OK':
                if on_disk.get(c) != n:
                    why.append('%s: the script wrote %d bars, the file '
                               'holds %s' % (c, n, on_disk.get(c, 'none')))
            elif st in ('NO BARS', 'NOT FOUND') and (
                    last is None or contract_key(c) > contract_key(last)):
                continue                # a contract not yet trading
            elif st == 'NO BARS' and with_bars and contract_key(c) < \
                    contract_key(min(with_bars, key=contract_key)):
                continue                # before the feed's history
            else:
                why.append('%s: %s%s' % (c, st, ' (%s)' % w if w else ''))
    return ('INCOMPLETE' if why else 'COMPLETE'), why


# ---------------------------------------------------------------------
# against a reference
# ---------------------------------------------------------------------
def best_shift(exp, ref):
    """The whole-hour (or one-minute) shift of the export's stamps that
    makes most of its bars equal the reference's, when one explains
    SHIFT_SHARE of them: (minutes, share) or None."""
    if not exp:
        return None
    best = None
    for k in SHIFTS:
        hit = sum(1 for m, b in exp.items()
                  if m + k in ref and same_bar(b, ref[m + k]))
        share = hit / float(len(exp))
        if best is None or share > best[1]:
            best = (k, share)
    return best if best and best[1] >= SHIFT_SHARE else None


def constant_offset(pairs):
    """The one price difference (export minus reference) shared by
    every pair of bars at the same stamp, or None."""
    off = None
    for a, b in pairs:
        d = [round(x - y, 9) for x, y in zip(a[:4], b[:4])]
        if len(set(d)) != 1 or (off is not None and d[0] != off):
            return None
        off = d[0]
    return off if off else None


def compare_contract(exp, ref, diagnose=True):
    """exp, ref: load()['bars']. The common span is from the later of
    the two first stamps to the earlier of the two last. diagnose: look
    for a shift of the stamps or one price offset behind a difference."""
    out = dict(export_bars=len(exp), reference_bars=len(ref), common=0,
               same=0, different=0, only_export=0, only_reference=0,
               outside_export=0, outside_reference=0, fields={},
               examples=[], shift=None, offset=None)
    if not exp or not ref:
        out['outside_export'], out['outside_reference'] = len(exp), len(ref)
        return out
    a, b = max(min(exp), min(ref)), min(max(exp), max(ref))
    out['span'] = [_stamp(a), _stamp(b)] if a <= b else None
    fields = collections.Counter()
    pairs = []
    for m, x in exp.items():
        if not a <= m <= b:
            out['outside_export'] += 1
        elif m not in ref:
            out['only_export'] += 1
            if len(out['examples']) < SHOW:
                out['examples'].append('%s only in the export' % _stamp(m))
        else:
            out['common'] += 1
            y = ref[m]
            if same_bar(x, y):
                out['same'] += 1
            else:
                out['different'] += 1
                pairs.append((x, y))
                bad = [n for n, p, q in zip('ohlcv', x, y)
                       if not same_bar((p,), (q,))]
                for n in bad:
                    fields[n] += 1
                if len(out['examples']) < SHOW:
                    out['examples'].append('%s differs in %s' % (
                        _stamp(m), ''.join(bad)))
    for m in ref:
        if not a <= m <= b:
            out['outside_reference'] += 1
        elif m not in exp:
            out['only_reference'] += 1
            if len(out['examples']) < SHOW:
                out['examples'].append('%s only in the reference'
                                       % _stamp(m))
    out['fields'] = dict(fields)
    if diagnose and (out['different'] or out['only_export'] or
                     out['only_reference']):
        sh = best_shift(exp, ref)
        if sh:
            out['shift'] = dict(minutes=sh[0], share=round(sh[1], 4))
        if pairs and out['different'] == out['common']:
            out['offset'] = constant_offset(pairs)
    return out


def compare(exp_loaded, ref_loaded):
    """Every contract of the reference that has bars before the gate,
    against the export. -> dict(rows, verdict, why)."""
    rows, why = [], []
    lacking = short = 0
    compared = diagnosed = 0
    for c in sorted(ref_loaded, key=contract_key):
        ref = ref_loaded[c]['bars']
        if not ref:
            continue                     # nothing before the gate
        if c not in exp_loaded:
            rows.append(dict(contract=c, missing=True,
                             reference_bars=len(ref)))
            lacking += 1
            continue
        r = compare_contract(exp_loaded[c]['bars'], ref,
                             diagnose=diagnosed < DIAGNOSE)
        r['contract'] = c
        rows.append(r)
        compared += 1
        if r['different'] or r['only_export'] or r['only_reference'] or \
                not r['common']:
            diagnosed += 1
            text = '%s: %d bars differ, %d only in the export, %d only in ' \
                'the reference, of %d at the same stamps' % (
                    c, r['different'], r['only_export'], r['only_reference'],
                    r['common'])
            if r['shift']:
                text += '; the export\'s stamps are %+d minutes off (%.0f %% ' \
                    'of its bars then agree)' % (r['shift']['minutes'],
                                                 100 * r['shift']['share'])
            if r['offset'] is not None:
                text += '; every price differs by the same amount (a ' \
                    'back-adjusted series?)'
            why.append(text)
        elif r['outside_reference']:
            short += 1
    if not compared and not lacking:
        return dict(rows=rows, verdict='NOT COMPARED', why=[
            'the reference has no bar before %s' % CX.REFUSE_FROM],
            compared=0)
    if why:
        verdict = 'DIFFERENT'
    elif lacking or short:
        verdict = 'SAME WHERE BOTH HAVE BARS'
        if lacking:
            why.append('%d contracts of the reference are not in the '
                       'export: %s' % (lacking, ', '.join(
                           r['contract'] for r in rows if r.get('missing'))))
        if short:
            why.append('%d contracts start later or end earlier in the '
                       'export than in the reference: %s' % (short, ', '.join(
                           r['contract'] for r in rows
                           if not r.get('missing') and
                           r['outside_reference'])))
    else:
        verdict = 'SAME'
    return dict(rows=rows, verdict=verdict, why=why, compared=compared)


# ---------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------
def run(folder, market=None, reference=None, progress=None):
    if market is None:
        roots = roots_in(folder)
        if len(roots) != 1:
            raise ExportCheckError(
                'name the market with --market: %s holds %s' % (
                    folder, ', '.join(roots) if roots else 'no contract '
                    'files'))
        market = roots[0]
    files = files_of(folder, market)
    loaded = {}
    for c in sorted(files, key=contract_key):
        if progress:
            progress(c)
        loaded[c] = load(files[c])
    desc = describe(loaded)
    summary = read_summary(folder, market)
    verdict, why = export_verdict(desc, summary)
    rep = dict(version=EC_VERSION, market=market,
               folder=os.path.abspath(folder), gate=CX.REFUSE_FROM,
               export=dict(desc, verdict=verdict, why=why,
                           script_summary=None if summary is None else dict(
                               version=summary['version'],
                               complete=summary['complete'],
                               time_zone=summary['time_zone'],
                               statuses=dict(collections.Counter(
                                   st for st, _n, _w in
                                   summary['rows'].values())))),
               reference=None)
    if reference:
        ref_files = files_of(reference, market)
        ref_loaded = {}
        for c in sorted(ref_files, key=contract_key):
            if progress:
                progress('reference ' + c)
            ref_loaded[c] = load(ref_files[c])
        rep['reference'] = dict(compare(loaded, ref_loaded),
                                folder=os.path.abspath(reference))
    return rep


def text(rep):
    e = rep['export']
    out = ['%s   %s   %s' % (rep['version'], rep['market'], rep['folder']),
           'A check of the data. No rule is run and no price is shown.',
           '',
           'THE EXPORT: %s' % e['verdict']]
    for w in e['why']:
        out.append('  - ' + w)
    s = e['script_summary']
    if s is None:
        out.append('  no summary of the export script in the folder '
                   '(files exported by hand have none)')
    else:
        out.append('  the export script: %s, %s, time zone %s; %s' % (
            s['version'], 'finished' if s['complete'] else 'NOT FINISHED',
            s['time_zone'], ', '.join('%d %s' % (n, k) for k, n in sorted(
                s['statuses'].items()))))
    out.append('  contracts %d   trading days %d (%s to %s)   before the '
               'gate %d, from it %d' % (
                   len(e['contracts']), e['trading_days'], e['first_day'],
                   e['last_day'], e['days_before_gate'], e['days_from_gate']))
    out.append('  days held by two contracts (the rolls): %d' %
               e['days_in_two_contracts'])
    out.append('')
    out.append('  %-10s %9s %6s  %-8s  %-8s' % ('contract', 'bars', 'days',
                                                'first', 'last'))
    for r in e['contracts']:
        out.append('  %-10s %9d %6d  %-8s  %-8s' % (
            r['contract'], r['bars'], r['days'], r['first'], r['last']))
    ref = rep['reference']
    if ref is not None:
        out.append('')
        out.append('AGAINST THE REFERENCE (%s), before %s: %s' % (
            ref['folder'], rep['gate'], ref['verdict']))
        for w in ref['why']:
            out.append('  - ' + w)
        out.append('  contracts compared: %d' % ref['compared'])
        out.append('  %-10s %9s %9s %9s %9s %9s' % (
            'contract', 'same', 'differ', 'only exp', 'only ref',
            'outside'))
        for r in ref['rows']:
            if r.get('missing'):
                out.append('  %-10s not in the export (%d bars in the '
                           'reference)' % (r['contract'],
                                           r['reference_bars']))
                continue
            out.append('  %-10s %9d %9d %9d %9d %9d' % (
                r['contract'], r['same'], r['different'], r['only_export'],
                r['only_reference'],
                r['outside_export'] + r['outside_reference']))
            for x in r['examples']:
                out.append('      ' + x)
        out.append('  "outside": bars before the later first stamp or '
                   'after the earlier last stamp of the two files; they '
                   'are not compared.')
    return '\n'.join(out) + '\n'


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def arg(k):
        if k in argv:
            i = argv.index(k)
            if i + 1 >= len(argv):
                raise ExportCheckError('%s needs a value' % k)
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
        return None

    try:
        market, reference, out = arg('--market'), arg('--reference'), \
            arg('--out')
        if len(argv) != 1:
            sys.stderr.write(__doc__)
            return 2
        rep = run(argv[0], market, reference, progress=lambda c: (
            sys.stderr.write('  reading %s\n' % c), sys.stderr.flush()))
    except ExportCheckError as exc:
        sys.stderr.write('STOPPED: %s\n' % exc)
        return 1
    if out:
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(rep, fh, indent=1, sort_keys=True)
    sys.stdout.write(text(rep))
    ok = rep['export']['verdict'] == 'COMPLETE' and (
        rep['reference'] is None or rep['reference']['verdict'] == 'SAME')
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main())
