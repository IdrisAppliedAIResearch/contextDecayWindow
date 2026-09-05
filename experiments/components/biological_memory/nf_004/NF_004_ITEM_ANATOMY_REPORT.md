# NF-004 Item-Level Anatomy Report

**Status:** `NO_STABLE_EVIDENCE_BLIND_PREDICTOR`; descriptive anatomy retained
**Standing:** post-outcome exploration on the spent NF-004 LoCoMo holdout
**Protocol commit:** `05132cda`
**Replay amendment:** `NF_004_ITEM_ANATOMY_AMENDMENT_001.md`
**Blind-feature commit:** `95f53eda`
**Population:** 1,098 primary items; 188 discordances
**Calls:** 0 embedding, 0 model, 0 cache misses
**Date:** August 29, 2026

## Result

The fixed 58-feature retrieval-time model does not predict whether pair ranking
or session-score inheritance wins reliably across conversations. Nested
leave-one-conversation-out logistic regression reaches out-of-fold ROC AUC
**0.5765**, average precision **0.7809**, and Brier score **0.2004**. The
within-conversation 10,000-permutation test gives **p=.1393**.

The no-feature, training-conversation-prevalence baseline has average precision
0.6687 and a better Brier score, **0.1947**. The model improves ranking somewhat
but worsens probability quality.

| Held-out conversation | Pair gains | Session rescues | AUC |
|---|---:|---:|---:|
| `conv-26` | 19 | 12 | .662 |
| `conv-30` | 11 | 5 | **.436** |
| `conv-43` | 21 | 8 | .583 |
| `conv-44` | 33 | 3 | **.444** |
| `conv-49` | 26 | 11 | .636 |
| `conv-50` | 30 | 9 | .615 |

The exploratory signal rule required AUC at least .65, permutation p at most
.05, and no held-out conversation below .50. It fails all three. The result is
`NO_STABLE_EVIDENCE_BLIND_PREDICTOR`, not a selector.

The label join exactly reproduces NF-004: **795 both pass, 115 both fail, 140
pair gains, and 48 session rescues**. Pair/session totals are 935/843.

## Anatomy

The strongest fixed descriptive feature is the difference in packed candidate
count, `pair - session`:

| Outcome class | Median count difference |
|---|---:|
| Pair gain | **0** |
| Session rescue | **+6** |
| Both pass | +2 |
| Both fail | +1 |

Its pooled pair-direction AUC is .339, or **.661 in the session-rescue
direction**. That direction is consistent in all six conversations: inverse
AUCs are .566, .591, .750, .747, .649, and .539. Session inheritance therefore
does not rescue by packing more candidates. At the median it rescues while pair
ranking fits six more. The plateau spends characters less efficiently but can
promote a deeply ranked required pair through a different pair in its session.

Three other clues are weaker but interpretable:

- Pair gains have lower maximum query cosine: median **.66 versus .70** for
  session rescues; pooled pair-direction AUC .378.
- Pair gains have a wider upper score tail (`p90 - p50`): median **.10 versus
  .09**, AUC .643. The direction is above .50 in all six conversations.
- Pair gains expose slightly more session-only alternatives: median **41 versus
  38**, AUC .632.

These observations suggest two regimes. When the query has one very strong
local match, session inheritance can use that match to carry otherwise weak
neighbors, occasionally rescuing required evidence. When relevance is spread
across a broader upper tail, pair ranking allocates the budget directly and
wins more often. This is a hypothesis from opened labels, not a demonstrated
moderator.

## Ablations

| Removed feature family | OOF AUC |
|---|---:|
| None | .576 |
| Query surface | .546 |
| Own-score shape | .564 |
| Session plateau shape | .579 |
| Rank disagreement | .602 |
| Packed-set contrast | **.497** |
| Budget frontier | .603 |

Packed-set contrast carries most of the weak pooled signal, consistent with the
candidate-count anatomy. Removing rank-disagreement or frontier features
improves AUC, showing that the full feature set is not a compact transferable
explanation. These are fixed family sensitivity checks, not a license to fit a
post-hoc reduced model.

## Integrity

Blind preflight produced 1,104 rows and 58 features twice with byte-identical
SHA-256 `af8d37cc6c23050cbbd27f39854e445b063134b805b316cecd30737c929bf608`.
The retained cache supplied every vector with zero misses and no new calls.
Features exclude answers, categories, evidence identities, evidence counts,
and evidence ranks. G6 outcomes were joined only after the feature artifact was
committed.

NF-004 did not retain historical selected-identity payloads, so current replay
cannot be compared to a 2026-08-13 payload manifest. Amendment 001 replaces
that unavailable check with byte-identical current blind replay plus exact G6
aggregate reproduction. Result JSON SHA-256 is
`bad0b63fb9094bf4508031e535182a3f08cfb992dbd742382bac7696977a2694`;
joined rows SHA-256 is
`3fd3a54f74a1ff1bb4137032e94665782684a6df9c4a41816a6cee170502c395`.

## Boundary

This result does not weaken NF-004's confirmed aggregate availability gain.
It says the 58 available score, plateau, rank, packing, frontier, and query
surface observables cannot safely choose between the two arms on a new LoCoMo
conversation. A successor needs a fresh corpus and a new information signal;
another combination of these opened-holdout features would be tuning.

Availability remains a surrogate for answer use. No reader, selector,
production change, or adoption is authorized.
