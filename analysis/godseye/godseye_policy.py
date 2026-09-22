#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — DATA PERMISSION POLICY (fail closed)
#
# One place decides what a session may show. It is consulted by the
# exporter (before anything is written), by the server (before anything
# is served) and by the replay reader (before any raw row is read), and
# it is deliberately free of research imports so it can run on a
# computer that holds only sanitized exports.
#
# Controlling rules, from the repository:
#   * MROF_YT_WAVE2_REGISTRATION.md §8 / §8.1 and mrofyt_pilot.py:
#     sessions >= BLIND_FROM (20260921) are the validation hold-out.
#     Weekly, only audit results, coverage, latency, feature
#     availability, funnels, fire/event COUNTS, build stamps and skip
#     reasons may be read from them. Markouts, directions and anything
#     event-level are withheld until the checkpoint read, which is a
#     separate, loud, permanent procedure this dashboard never performs.
#   * MROF_EXPOSED_PILOT_DEV_DAYS.json (written by the pilot): a session
#     is EXPOSED only when the pilot has labelled it EXPOSED_PILOT_DEV.
#     A date before the hold-out is NOT automatically exposed.
#   * the outcome lock (analysis/mrof/MROF_V1_STATE_C_AUTHORIZED.json) is
#     never created or read here; December unlocks nothing by itself.
#
# Where the rules could be read two ways, the narrower reading is used
# and named: a session missing from the ledger is PROTECTED whatever its
# date; an unreadable ledger makes every session UNKNOWN; a request that
# mixes an inspectable session with any other is refused whole.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import json
import os

POLICY_VERSION = 'MROF-GODSEYE-POLICY-1.0'

# labels written by mrofyt_pilot (quoted, not imported: see header)
EXPOSURE_LABEL = 'EXPOSED_PILOT_DEV'
BLIND_LABEL = 'VALIDATION_BLIND_MARKOUTS_WITHHELD'
DEFAULT_BLIND_FROM = '20260921'

# session classes
EXPOSED = 'EXPOSED'                 # pilot labelled it exposed
BLIND = 'BLIND'                     # validation hold-out (labelled or by date)
PROTECTED = 'PROTECTED_UNLISTED'    # before the hold-out, never labelled
UNKNOWN = 'UNKNOWN'                 # the ledger could not be read

# what each class may carry. `counts` always come from a released
# report (never recomputed here); `operational` is recorder/audit
# health; `events`, `features` and `replay` are event-level.
PERMITTED = {
    EXPOSED: frozenset(('operational', 'counts', 'events', 'features',
                        'replay')),
    BLIND: frozenset(('operational', 'counts')),
    PROTECTED: frozenset(('operational', 'counts')),
    UNKNOWN: frozenset(('operational',)),
}

# fields that are event-level or outcome-bearing wherever they appear;
# the exporter strips them from any record of a non-EXPOSED session and
# tests_godseye.py scans the whole snapshot for them
EVENT_LEVEL_FIELDS = frozenset((
    'direction', 't', 't_start', 't_end', 'level_px', 'px', 'mid',
    'markout', 'markouts', 'markouts_signal_source', 'ci95_median',
    'ci95_mean', 'median', 'mean', 'approach', 'fires', 'events',
    'windows_list', 'features', 'aggr_z', 'aggr_dir', 'progress_ticks',
    'replenish_z', 'opp_flip_z', 'wall_z', 'control_z', 'delta_z',
))


class PolicyError(PermissionError):
    """A request the policy refuses. Carries the classes it saw so the
    refusal can be shown, never the data it refused."""


class Policy(object):
    def __init__(self, blind_from=DEFAULT_BLIND_FROM, ledger_days=None,
                 ledger_path=None, ledger_error=None, synthetic=False):
        self.blind_from = str(blind_from) if blind_from else None
        self.ledger_days = dict(ledger_days) if ledger_days is not None \
            else None
        self.ledger_path = ledger_path
        self.ledger_error = ledger_error
        self.synthetic = bool(synthetic)

    # ---- construction ------------------------------------------------
    @classmethod
    def from_files(cls, ledger_path, blind_from=DEFAULT_BLIND_FROM,
                   synthetic=False):
        """Reads the exposure ledger. A missing or malformed ledger is
        recorded as an error and makes every session UNKNOWN; it never
        raises, because health views must still work."""
        days, err = None, None
        try:
            with open(ledger_path) as fh:
                doc = json.load(fh)
            days = {}
            for d in doc.get('exposed_days', []):
                s, lab = d.get('session'), d.get('label')
                if s and lab:
                    days[str(s)] = lab
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            err = '%s: %s' % (ledger_path, exc)
        return cls(blind_from, days, ledger_path, err, synthetic)

    # ---- classification ----------------------------------------------
    def session_class(self, session):
        if session is None:
            return UNKNOWN
        if self.ledger_days is None:
            return UNKNOWN
        s = str(session)
        lab = self.ledger_days.get(s)
        if lab == EXPOSURE_LABEL:
            return EXPOSED
        if lab == BLIND_LABEL:
            return BLIND
        if lab is not None:
            return UNKNOWN            # a label this policy does not know
        if self.blind_from and s >= self.blind_from:
            return BLIND
        return PROTECTED

    def permits(self, session, what):
        return what in PERMITTED[self.session_class(session)]

    def may_inspect(self, session):
        return self.session_class(session) == EXPOSED

    def require_inspectable(self, sessions, what='events'):
        """All-or-nothing: every session must permit `what`, else the
        whole request is refused with the classes named."""
        sessions = [s for s in sessions]
        if not sessions:
            raise PolicyError('no session named; nothing to permit')
        classes = {str(s): self.session_class(s) for s in sessions}
        bad = {s: c for s, c in classes.items()
               if what not in PERMITTED[c]}
        if bad:
            raise PolicyError(
                'refused: %s not permitted for %s (%s)%s'
                % (what, ', '.join('%s=%s' % kv for kv in sorted(bad.items())),
                   'request mixed inspectable and protected sessions'
                   if len(bad) < len(classes) else 'no inspectable session',
                   '; exposure ledger unreadable: %s' % self.ledger_error
                   if self.ledger_error else ''))
        return classes

    # ---- reporting ---------------------------------------------------
    def describe(self):
        days = self.ledger_days or {}
        return dict(policy=POLICY_VERSION, blind_from=self.blind_from,
                    exposure_ledger=self.ledger_path,
                    exposure_ledger_error=self.ledger_error,
                    exposure_ledger_days=len(days),
                    exposed_sessions=sorted(s for s, l in days.items()
                                            if l == EXPOSURE_LABEL),
                    blind_labelled_sessions=sorted(
                        s for s, l in days.items() if l == BLIND_LABEL),
                    synthetic=self.synthetic,
                    classes=dict((k, sorted(v)) for k, v in PERMITTED.items()),
                    rules=[
                        'a session is EXPOSED only when the exposure ledger '
                        'labels it %s' % EXPOSURE_LABEL,
                        'sessions >= %s are the validation hold-out: counts '
                        'only, never direction, timestamps, features, '
                        'markouts or replay' % self.blind_from,
                        'a session before the hold-out that the ledger does '
                        'not list is PROTECTED, whatever its date',
                        'an unreadable ledger makes every session UNKNOWN '
                        '(operational health only)',
                        'a request mixing an inspectable session with any '
                        'other is refused whole',
                        'the outcome-unlock file is never created or read; '
                        'the checkpoint is a separate procedure',
                    ])


def strip_event_level(obj):
    """Remove event-level and outcome-bearing keys from a record tree.
    Used on any record of a non-EXPOSED session as a second line behind
    the explicit allowlists in the exporter."""
    if isinstance(obj, dict):
        return {k: strip_event_level(v) for k, v in obj.items()
                if k not in EVENT_LEVEL_FIELDS}
    if isinstance(obj, list):
        return [strip_event_level(v) for v in obj]
    return obj


def scan_for_event_level(obj, path='$'):
    """Every path in `obj` whose key is an event-level field. Used by the
    tests on the finished snapshot; an empty list is the proof."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = '%s.%s' % (path, k)
            if k in EVENT_LEVEL_FIELDS:
                hits.append(p)
            hits.extend(scan_for_event_level(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_for_event_level(v, '%s[%d]' % (path, i)))
    return hits


def outcome_lock_state(mrof_dir):
    """Reports whether the State-C outcome lock file exists. Reads only;
    this module never creates it and the dashboard has no path that
    could."""
    p = os.path.join(mrof_dir, 'MROF_V1_STATE_C_AUTHORIZED.json')
    return dict(path=p, exists=os.path.exists(p),
                note='absent = outcomes locked; this dashboard never '
                     'creates it')
