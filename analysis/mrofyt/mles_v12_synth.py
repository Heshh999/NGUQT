#!/usr/bin/env python3
# ======================================================================
# MLES-CAPTURE-1.2 SYNTHETIC RUN GENERATOR — TEST FIXTURES ONLY.
# Writes a self-consistent run (four CSVs + manifest, exact counts and
# hashes, build 1.2.1 fields) in the recorder's format so the streaming
# auditor and the outcome-blind runner can be exercised at session
# scale without any market data. Synthetic rows verify CODE BEHAVIOR
# only; they are never market evidence and never enter research.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import datetime as _dt
import hashlib
import json
import os

import mles_v12_adapter as AD

TICK = 0.25


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _iso(t):
    s = int(t)
    return '%s.%07dZ' % (_dt.datetime.utcfromtimestamp(s).strftime(
        '%Y-%m-%dT%H:%M:%S'), int(round((t - s) * 1e7)))


def synth_run(d, n_depth=300000, instrument='NQ', session='20260902',
              cid='synth-cid', run_no=1, t0=None, dt_step=0.0005,
              price_path=None, trade_every=40, quote_every=25,
              contract=None, seed=0):
    """price_path(i) -> mid price (default flat 15000). Trades alternate
    aggressor; depth cycles ADD/UPDATE/REMOVE over levels 0..9 on both
    sides around the current mid. Returns the manifest path."""
    os.makedirs(d, exist_ok=True)
    contract = contract or ('%s SEP26' % instrument)
    rid = '%s-R%03d' % (cid, run_no)
    com = 'MLES-CAPTURE-1.2,%s,%s,1,%s,%s,%s,' % (cid, rid, session,
                                                  instrument, contract)
    base = 'MLES12_%s_%s_%s_%s' % (instrument, contract.replace(' ', '_'),
                                   session, rid)
    paths = {k: os.path.join(d, base + '_%s.csv' % k) for k in AD.STREAMS}
    fh = {k: open(paths[k], 'w') for k in AD.STREAMS}
    for k in AD.STREAMS:
        fh[k].write(','.join(AD.HEADERS[k]) + '\n')
    if t0 is None:
        t0 = (_dt.datetime(2026, 9, 2, 13, 30, tzinfo=_dt.timezone.utc)
              - _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
              ).total_seconds()
    seq = 0
    ss = dict(quotes=0, trades=0, depth=0, quality=0)
    state = dict(t=t0)

    def row(k, stream, t, rest):
        nonlocal seq
        seq += 1
        ss[k] += 1
        fh[k].write(com + '%s,%d,%d,%s,%s,%d,%s\n'
                    % (stream, seq, ss[k], _iso(t), _iso(t - 0.25),
                       int((t - t0) * 1e7), rest))

    def mid_at(i):
        return 15000.0 if price_path is None else price_path(i)

    nbid = nask = nadd = nupd = nrem = 0
    t = t0
    row('quality', 'QUALITY', t, 'SESSION_START,runId=%s' % rid)
    row('quality', 'QUALITY', t, 'BOOK_RESYNC_START,declaredDepth=10')
    for i in range(n_depth):
        t += dt_step
        m = mid_at(i)
        bid = round((m - TICK / 2) / TICK) * TICK
        ask = bid + TICK
        side = 'BID' if i % 2 == 0 else 'ASK'
        act = ('ADD', 'UPDATE', 'REMOVE')[i % 3]
        lvl = (i // 2) % 10
        px = bid - lvl * TICK if side == 'BID' else ask + lvl * TICK
        row('depth', 'DEPTH', t, 'MBP,%s,%s,%d,%.2f,%d,'
            % (act, side, lvl, px, 5 + i % 7))
        if side == 'BID':
            nbid += 1
        else:
            nask += 1
        if act == 'ADD':
            nadd += 1
        elif act == 'UPDATE':
            nupd += 1
        else:
            nrem += 1
        if i == 19:
            row('quality', 'QUALITY', t,
                'BOOK_READY,bidLevels=10 askLevels=10')
        if i % quote_every == 0:
            row('quotes', 'QUOTE', t, 'BID,%.2f,12,%.2f,12,%.2f,9,'
                % (bid, bid, ask))
        if i % trade_every == 0:
            j = i // trade_every
            # deterministic but dispersed sizes/sides so causal robust
            # baselines have a non-zero MAD (a constant tape would make
            # every z None by the frozen definition)
            h = (j * 7919 + seed * 104729) % 97
            buy = (h % 3) != 0 if (j % 2 == 0) else (h % 3) == 0
            qty = 1 + h % 9
            row('trades', 'TRADE', t, '%.2f,%d,%.2f,12,%.2f,9,,%s,'
                'QUOTE_TEST_v1,HIGH,' % (ask if buy else bid, qty, bid, ask,
                                          'BUY' if buy else 'SELL'))
    row('quality', 'QUALITY', t, 'SHUTDOWN,orderly')
    for k in AD.STREAMS:
        fh[k].close()
    man = dict(schema='MLES-CAPTURE-1.2', captureInstanceId=cid, runId=rid,
               closeReason='SHUTDOWN', session=session,
               instrument=instrument, contract=contract, bookType='MBP',
               declaredDepth=10, flushPolicySeconds=30,
               aggressorSource='ABSENT-feed; inferred QUOTE_TEST_v1',
               firstRecvUtc=_iso(t0), lastRecvUtc=_iso(t),
               lastExchUtc=_iso(t - 0.25), firstEventSeq=1,
               lastEventSeq=seq, firstSegId=1, lastSegId=1,
               connectionSegments=1,
               firstQuoteSeq=1, lastQuoteSeq=ss['quotes'],
               firstTradeSeq=1, lastTradeSeq=ss['trades'],
               firstDepthSeq=1, lastDepthSeq=ss['depth'],
               firstQualitySeq=1, lastQualitySeq=ss['quality'],
               gaps=0, duplicates=0, reversals=0, queueOverflows=0,
               droppedRows=0, writeErrors=0, reconnects=0, crossed=0,
               bookResets=0, maxBidLevelSeen=10, maxAskLevelSeen=10,
               maxBidLevelRun=10, maxAskLevelRun=10, recorderBuild='1.2.1',
               depthBid=nbid, depthAsk=nask, depthAdd=nadd,
               depthUpdate=nupd, depthRemove=nrem)
    for k in AD.STREAMS:
        man[k] = dict(present=True, file=os.path.basename(paths[k]),
                      bytes=os.path.getsize(paths[k]), rows=ss[k],
                      sha256=_sha(paths[k]))
    mp = os.path.join(d, base + '_manifest.json')
    json.dump(man, open(mp, 'w'))
    _ = state
    return mp
