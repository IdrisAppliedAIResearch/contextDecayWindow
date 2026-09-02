# DA-004 Evidence-Blind Pack Perturbation Report

**Status:** `BENEFIT_SIGNAL_ONLY`; harm remains unpredictable
**Standing:** post-outcome exploration on spent NF-004 LoCoMo
**Protocol commit:** `27514464`
**Blind-perturbation commit:** `05546afd`
**Population:** 1,098 primary questions; 25,941 primary edge actions
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 29, 2026

## Result

The complete packing perturbation carries a stable evidence-blind signal for
where a temporal edge can improve exact evidence delivery. The fixed grouped
benefit model reaches out-of-conversation AUC **.8234**:

| Conversation | Benefits | AUC |
|---|---:|---:|
| `conv-26` | 16 | .907 |
| `conv-30` | 4 | .842 |
| `conv-43` | 12 | .814 |
| `conv-44` | 1 | .960 |
| `conv-49` | 19 | .800 |
| `conv-50` | 5 | .935 |

All six conversations exceed .50, so the fixed descriptive disposition is
`NEW_SIGNAL_PRESENT` for benefit. Average precision is **.0273** against a
57/25,941 positive rate, and Brier score is .00222. The low absolute precision
matters: useful edges remain rare even though their ranking is substantially
better than chance.

The safety result fails. The grouped harm model has AUC **.5039** and
`NO_STABLE_PACK_SIGNAL`. Conversation 44 reverses to .473; three conversations
contain no harmful edge and are not evaluable. A benefit ranking is therefore
not a safe admission rule.

## What Carries Benefit

The strongest fixed univariate is IDF-weighted query coverage of the complete
`ADDED` set, raw AUC **.8313**. Its direction is above .50 in all six
conversations. Median added-set coverage is:

| Outcome | Median added query coverage |
|---|---:|
| `BENEFIT` | **.229** |
| `HARM` | .146 |
| `NEUTRAL` | .073 |

Benefits also add more query-relevant material by direct score: median added
score mean is .462 versus .420 for harms and .336 for neutral actions. Added
query coverage is stronger than neighbor-only attribution because it includes
the downstream candidates whose changed fit caused DA-003 to stop.

The exact labels reproduce DA-003: 57 benefits, comprising 48 neighbor-carried
and 9 downstream-carried; 40 harms; and 25,844 neutral actions. Thus the signal
is attached to the actual set perturbation rather than falsely credited to the
linked neighbor.

## What Does Not Solve Safety

Harm has strong descriptive univariates but no stable combined predictor.
Displaced query-token count has pooled raw AUC .801, and displacement size also
ranks harms, yet conversation-specific prevalence is concentrated: 5 harms in
`conv-26`, 13 in `conv-43`, and 22 in `conv-44`, with none in the other three.
The fixed grouped model does not transfer into conversation 44.

This repeats the central asymmetry. Query-facing text can identify plausible
new information, but evidence-blind retrieval observables still cannot certify
that displaced low-priority material is dispensable. A rule that follows only
the benefit score would recover opportunities while remaining blind to the
known loss mechanism.

## Interpretation

The new architectural signal is **added-set query complementarity**, evaluated
after exact packing rather than on the neighbor alone. This is more specific
than “follow adjacent context”: simulate the edge's deterministic packing
effect, then inspect whether the entire admitted set contributes query-facing
information.

It is not yet an evidence-blind rule. A successor needs an independently safe
loss control, likely a protection or reservation mechanism rather than another
attempt to infer evidence absence from low cosine. Any such mechanism must be
registered and evaluated on fresh conversations before selecting a threshold.

## Integrity and Boundary

Blind construction used DA-003 identities, DA-002 sealed scores and costs, and
locked corpus text. It opened no cache and made no embedding or model call.
All 26,100 blind rows replayed byte-identically. The primary join reproduced
935/1,098 direct complete items and all fixed DA-003 transition counts.

Result SHA-256 is
`04480137adfb269db033f72fd9530d6d84278e9e7ac861e8c0f600e53b3c5f87`;
edge-label SHA-256 is
`d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca`.

This spent-corpus result authorizes no threshold, gate, implementation change,
reader claim, production policy, or adoption.
