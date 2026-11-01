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


def record_holdout_read(rep, path, version):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=version, sessions=rep['sessions_inspected']))
    old['rule'] = ('Replay holdout sessions are read once by each '
                   'registered wave; a later read of NEW rules on them is '
                   'not a fresh test.')
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def record_exposure(rep, path, version):
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
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
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)
