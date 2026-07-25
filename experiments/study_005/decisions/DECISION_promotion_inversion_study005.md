# Decision: Study 005 Promotion Inversion

**Status:** Accepted and locked for Study 005

**Date:** July 22, 2026

**Author authorization:** Muzaffer authorized Study 005 to proceed and this decision to be recorded through the July 22, 2026 execution request.

## Finding

Study 004's read path was operational, but the promoted store omitted every later-domain rubric-critical plant. The four-filter write path selected nine early civil episodes and one generic episode from each later domain. Retrieval could not recover facts that formation had excluded.

## Decision

Replace selective write-time promotion with a two-stage inversion:

1. Store every completed conversational turn in an append-only raw episodic store, including acknowledgments and other non-content turns.
2. At topic transitions and the turn-111 flush, run the locked extractive-dreaming algorithm over the outgoing topic's undreamed snapshot.
3. Write at most three salience-ranked, deduplicated, verbatim records per topic to distilled LTM, subject to the salience floor and honest sparse-topic marker.
4. Point the existing LTM retrieval tier at distilled LTM.

The dream pass uses no inference calls. Every content-bearing distilled record must be a verbatim span of a source episode and carry resolvable episode/turn provenance.

## Retirements

The Study 003 novelty, repetition, association, and emotional filters retire from the Study 005 write path. The weighted threshold, all-or-nothing bypass, and Study 004 association-decoupling retire with them. Their code may remain available for the committed Study 004 control, but none may execute in the Study 005 treatment.

Topic assignment, canonical consolidation, purity instrumentation, the probe-bridge guard, STM retrieval, tier-neutral arbitration, deduplication, and tagged context rendering remain in force.

## Locked parameters

- Salience: named-entity count + 2 × numeric-token count
- Extractor: documented capitalized-sequence fallback
- Near-duplicate threshold: cosine similarity ≥ 0.95
- Per-topic cap: C = 3
- Salience floor: F = 2
- Distilled retrieval: top-M = 5

## Consequence

Study 005 moves selectivity from event-time filtering to deterministic offline-style consolidation at registered cadence. Bar 1 evaluates formation directly before Bar 2 is allowed to interpret retrieval.
