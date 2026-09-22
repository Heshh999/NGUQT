#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — SYNTHETIC DEMONSTRATION BUILDER
#
# Builds a clearly labelled synthetic capture folder plus every report
# the dashboard reads, using the project's own synthetic recorder-format
# generator and the LIBRARY entry points of the audit, runner, pilot,
# wave two and recovery tools. It never calls a tool's command line, so
# it never touches the repository's exposure ledger: the demo has its
# own ledger inside the demo folder.
#
# Everything it produces is labelled synthetic. Nothing here is market
# evidence, and a zero fire count on a sine-wave tape is expected.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import datetime as _dt
import glob
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ('..', '../mrofyt', '../mrof', '../rvmr'):
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, _p)))

import mles_v12_audit as AU            # noqa: E402
import mles_v12_synth as SY            # noqa: E402
import mrofyt_pilot as PI              # noqa: E402
import mrofyt_recover as RC            # noqa: E402
import mrofyt_runner as RN             # noqa: E402
import mrofyt_wave2 as W2              # noqa: E402

DEMO_VERSION = 'MROF-GODSEYE-DEMO-1.0'
SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921', '20260922')


def _dump(obj, path):
    tmp = path + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(obj, fh, default=str, indent=1)
    os.replace(tmp, path)


def build(demo_dir, n_depth=30000, quiet=False):
    cap = os.path.join(demo_dir, 'capture')
    rep = os.path.join(demo_dir, 'reports')
    os.makedirs(cap, exist_ok=True)
    os.makedirs(rep, exist_ok=True)
    say = (lambda *a: None) if quiet else print
    path = lambda i: 15000.0 + 3.0 * math.sin(2 * math.pi * (i * 0.05) / 900.0)  # noqa: E731
    for i, ses in enumerate(SESSIONS):
        d = _dt.datetime.strptime(ses, '%Y%m%d')
        t0 = _dt.datetime(d.year, d.month, d.day, 13, 30,
                          tzinfo=_dt.timezone.utc).timestamp()
        for inst in ('NQ', 'MNQ'):
            # one capture instance per instrument, as the recorder does
            SY.synth_run(cap, n_depth=n_depth, dt_step=0.05, price_path=path,
                         trade_every=10, quote_every=5,
                         cid='demo%d%s' % (i, inst.lower()),
                         session=ses, seed=i, instrument=inst, t0=t0)
    # one dead orphan pair (both instruments), aged, so the recovery and
    # health views have something to show
    for mp in glob.glob(os.path.join(cap, '*20260909_demo6*-R001_manifest.json')):
        man = json.load(open(mp))
        os.remove(mp)
        old = time.time() - 3 * 86400
        for k in ('quotes', 'trades', 'depth', 'quality'):
            p = os.path.join(cap, man[k]['file'])
            os.rename(p, p + '.partial')
            os.utime(p + '.partial', (old, old))
    say('synthetic capture ->', cap)
    # reports through library entry points only
    _dump(AU.audit_capture(cap), os.path.join(rep, 'audit.json'))
    led = RN.Runner(cap, ('NQ', 'MNQ')).run()
    _dump(led, os.path.join(rep, 'ledger.json'))
    prep, prunner = PI.run_pilot(cap)
    _dump(prep, os.path.join(rep, 'pilot.json'))
    ledger_path = os.path.join(demo_dir, 'MROF_EXPOSED_PILOT_DEV_DAYS.json')
    PI.write_exposure_ledger(prep, ledger_path)          # the DEMO's ledger
    PI.write_windows(prunner, os.path.join(rep, 'windows.json'))
    w2, _ = W2.run_wave2(cap, mode='real')
    w2p, _ = W2.run_wave2(cap, mode='placebo')
    _dump(dict(real=w2, placebo=w2p,
               paired=W2.paired_summary(w2, w2p, PI.BLIND_FROM),
               wave2=w2['wave2'], mode='both', blind_from=w2['blind_from'],
               sessions_inspected=w2['sessions_inspected'],
               wave_one_raw_fires=w2['wave_one_raw_fires'],
               w2_windows=w2['w2_windows'],
               w2_input_availability=w2['w2_input_availability'],
               arm_b=w2['arm_b'], families=w2['families'],
               not_in_this_version=w2['not_in_this_version']),
          os.path.join(rep, 'wave2.json'))
    _dump(RC.recover_directory(cap, dry_run=True),
          os.path.join(rep, 'recovery.json'))
    cfg = dict(capture_dir=cap, reports_dir=rep, exposure_ledger=ledger_path,
               out_dir=os.path.join(demo_dir, 'godseye_out'),
               windows=os.path.join(rep, 'windows.json'), synthetic=True,
               blind_from=PI.BLIND_FROM, port=8765, bind='127.0.0.1',
               demo=DEMO_VERSION,
               note='SYNTHETIC DEMONSTRATION: generated fixtures, not market '
                    'data')
    _dump(cfg, os.path.join(demo_dir, 'godseye.config.json'))
    say('reports ->', rep)
    say('config  ->', os.path.join(demo_dir, 'godseye.config.json'))
    return cfg


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('usage: python godseye_demo.py <demo folder> [--small]')
        return 2
    cfg = build(argv[0], n_depth=8000 if '--small' in argv else 30000)
    print('next: python godseye_export.py --config %s'
          % os.path.join(argv[0], 'godseye.config.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
