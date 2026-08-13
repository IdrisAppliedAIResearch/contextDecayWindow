# NF-003 Preflight Surrogate Audit - Session Touch Is Not Evidence Delivery

**Status:** `PREFLIGHT SURROGATE FAIL - PROPOSED REGISTRATION CLOSED`
**Disposition:** `UNREGISTERED EXPLORATION; STRICT-EVIDENCE REGRESSION CHARACTERIZED`
**Artifact:** `artifacts/surrogate_audit.json`
**Artifact SHA-256:** `c71b7556b47397431aad01b5a1434d91af0fa9c2a27a3e51fb52ff478a619a5b`
**Part 1 commit:** `a96630ea5557456987bb81cb03f1c43400040e2b`
**Model calls:** 0
**Embedding calls:** 0
**Date:** August 13, 2026

## 1. Why registration stopped

Part 1's primary measure was whether packing touched any session named in
LongMemEval's `answer_session_ids`. That measure is valid when the candidate is
the whole session: selecting it delivers every answer-bearing turn. It is not
valid when the candidate is one episode. Selecting an unrelated episode from
an answer session touches the session without delivering the answer.

The mandatory PF9 question therefore fires:

> Can session-touch pass while answer-bearing evidence is absent? **Yes.**

The treatment records 94 such false hits. A gate on session-touch could certify
the ranking change while the property it names - evidence delivery - got worse.
The proposed NF-003 registration is closed before lock rather than built around
that surrogate.

## 2. Like-for-like reconstruction

The audit uses the same 465 Part 1 items with turn-level `has_answer` flags and
reconstructs both arms from committed identities:

- Baseline: episodes inherit their session's committed EC-002 cosine rank.
- Treatment: episodes use their own committed Part 1 cosine rank.
- Packing: the same 32,000-character skip-on-overflow policy.
- Strict evidence: at least one delivered episode contains a `has_answer` turn.

The coarse measure reproduces Part 1 exactly before the strict result is read.

| Measure | Baseline | Treatment | Gains | Losses | Ties |
|---|---:|---:|---:|---:|---:|
| Session touched | 396 | 445 | 49 | 0 | 416 |
| **Answer episode delivered** | **388** | **351** | **26** | **63** | **376** |

The apparent gain reverses from net +49 to net -37. Session-level evidence
overstates baseline delivery by 8 items and treatment delivery by 94.

## 3. What this says about the mechanism

This is not merely an instrument that cannot discriminate. Once the outcome is
measured at the unit the reader receives, episode-level ranking is harmful on
this corpus under this budget and packing policy: it loses 63 items while
gaining 26. The session-touch instrument hid that regression.

No registered `NULL` or failure disposition is applied because no NF-003 bars
were locked before these numbers existed. The honest status is an unregistered,
deterministic characterization that closes this proposed registration.

## 4. NF-002 boundary

The same audit checks NF-002's candidate-unit contrast on the 465 labelled
items. Whole-session candidates deliver strict evidence on 375 items;
session-ranked episode candidates deliver it on 388, with 17 gains, 4 losses,
and 444 ties. NF-002's packing-unit signal survives under the strict measure,
but as net +13 rather than the registered session-touch net +16. Its formal
`CARRIES_SIGNAL - CHARACTERIZED` disposition is not rewritten by this posthoc
audit.

## 5. Reproduction and scope

`src/analysis/nf003_surrogate_audit.py` reconstructs the item matrix and writes
the artifact. It first reproduces Part 1's 396/445 and 49/0 session-touch result,
then emits the strict comparison. A second run is byte-identical. The targeted
test file asserts both measures, both surrogate gaps, the 465/5 population
boundary, and zero model or embedding calls.

Five LongMemEval items lack turn-level flags and remain unmeasured by the strict
audit. Nothing here imputes their treatment outcomes. No live evaluation,
adoption, similarity replacement, or posthoc disposition is authorized.

## 6. Successor

The question remains open on another corpus because this is unregistered and
LongMemEval is exhausted. LoCoMo was acquired and split before any QA content
was opened. Its development conversations may be used to design a strict
episode-evidence instrument; its six holdout conversations remain sealed until
that successor's registration and PF1-PF10 are committed.
