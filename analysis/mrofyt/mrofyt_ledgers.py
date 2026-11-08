#!/usr/bin/env python3
"""mrofyt_ledgers.py - the two read ledgers the registered waves write

One copy of what waves seven to thirteen each record after a held-out
read, keyed by the wave's version string:

    record_holdout_read   MROF_REPLAY_HOLDOUT_EXPOSURE.json: which wave
                          read which replay sessions
    record_exposure       MROF_EXPOSED_PILOT_DEV_DAYS.json: every session
                          an --unblind read inspected becomes
                          EXPOSED_PILOT_DEV for good

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import json
import os

import mrofyt_pilot as PI


def _write(path, doc):
    """Write and close at once: every record_* call reads back the file
    the call before it wrote, so the write must be on disk before it
    returns, under any Python (PyPy closes an unreferenced file only
    when its garbage collector gets to it). The bytes are the same as
    json.dump's to an open file."""
    with open(path, 'w') as fh:
        json.dump(doc, fh, indent=1)


def record_holdout_read(rep, path, version):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            with open(path) as fh:
                old = json.load(fh)
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=version, sessions=rep['sessions_inspected']))
    old['rule'] = ('Replay holdout sessions are read once by each '
                   'registered wave; a later read of NEW rules on them is '
                   'not a fresh test.')
    _write(path, old)
    return len(old['reads'])


def record_history_read(rep, path, version):
    """MROF_MINUTE_HISTORY_EXPOSURE.json: which wave read which years of
    minute exports in its judging (--unblind) mode. Those years are read
    once by each registered question."""
    import datetime as _dt
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            with open(path) as fh:
                old = json.load(fh)
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=version, first=rep.get('first_session'),
        last=rep.get('last_session'), n=rep.get('n_trades'),
        at=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    old['rule'] = ('The minute-export years before 2019-06-01 are judged '
                   'once by each registered question; a later read of NEW '
                   'rules on them is not a fresh test.')
    _write(path, old)
    return len(old['reads'])


def record_exposure(rep, path, version):
    old = []
    if os.path.exists(path):
        try:
            with open(path) as fh:
                old = json.load(fh).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    for s in rep['sessions_inspected']:
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=PI.EXPOSURE_LABEL,
                         exposed_by=version, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=version,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if version not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(version)
    days = sorted(by.values(), key=lambda d: d['session'])
    _write(path, dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded.',
                   exposed_days=days))
    return len(days)
