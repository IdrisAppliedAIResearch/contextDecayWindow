# AF-PRE-009 RESULTS — what limits the 56/120 (audit of the 64 misses)

Plan `6aa2a019`, PF4 measurement `0e98b31d`, Amendment 001 `ba3e9faf` (all before
interpretation). Reproduction gate: ckpt2 ungated over all turns recomputed by importing the
frozen AF-PRE-005 contract — **56/120 exact, asserted before any category was computed**.

## The 64 misses, priority-ordered mechanical attribution (first match wins)

| category | n | what it means |
|---|---|---|
| **E1 wrong-evidence** | **10** | the model returned *another* annotated evidence turn of the same item — answer-bearing evidence, just not the earliest |
| E2 duplicate-text | 0 | unreachable at PF4 (no item has a duplicate copy of gold) |
| **E3 answer-elsewhere** | **0** | the model **never** won by landing on the answer-stating turn |
| E4 true-ranking-fail | 18 | gold states the answer and was beaten (7 near: rank 2–3; 11 far: ≥ 4) |
| E5 residual | 36 | neither gold nor prediction contains the answer value |

Answer-presence × correctness over all 120: **32/52 (61.5%) when the answer value is at the
anchor vs 24/68 (35.3%) when it is not — Fisher p = .0056, OR 2.93.**

## Amendment 001 sub-partition: where the answer value actually lives

| class (all 120) | items | accuracy | misses |
|---|---|---|---|
| X4 answer value **at** gold | 52 | **61.5%** | 20 |
| X3 answer value in **other** turn text, not at gold | 9 | **11%** | 8 |
| X2 answer value **only in session date header** | 9 | 56% | 4 |
| X1 answer value **nowhere in any text** | 50 | 36% | 32 |

The registered rule fired (X1+X2 = 36 ≥ 18): the dominant limiting factor is **the candidate
unit and answer location, not the ranking margin**.

## Reading (what the numbers carry, and what they don't)

**1. Half the error mass is items the turn-level contract cannot represent.** 32 of 64 misses
(X1) have answers that appear nowhere in the conversation text — counts, comparisons, yes/no,
paraphrased dates. The reranker still wins 18/50 of these by matching the event, so they are hard,
not impossible; but "find the turn whose text matches the question" is not the operation those
items require. Category 1 (multi-hop) and 3 carry 19 of them.

**2. The reranker matches *topic*, not *answerhood* — and it does so even when it is lost.**
On the 9 X3 items (the answer value is present in the conversation but not at the anchor) it scores
**1/9**, and E3 = 0 means it never even landed on the turn stating the answer: it picks a third,
topically similar turn. So this is not "it anchors too early/late"; it has no representation of
"which turn *answers*" versus "which turn is about the same thing". That is the same lever
AF-PRE-005 identified — the task contract, not the architecture — and it points at the concrete
training change: answer-stating turns must appear as **hard negatives** on event-anchor items.

**3. Session metadata is dropped and it matters only a little.** 4 misses (X2) are date answers
recoverable only from `session_N_date_time`, which `arms.load_conversations` discards; but X2
accuracy is 56%, near the average, so folding headers into the candidate text is a cheap, small,
well-scoped fix, not the big one.

**4. Label identity is worth 10 items (66/120).** Under AF-PRE-001's *own* registered rule ("any
annotated-introducing evidence turn counts"), 10 misses — 9 of them cat-1 — are not errors.
AF-PRE-005's number and verdict are unchanged (its registered scoring was strict earliest); this
is a statement about what the error mass is made of, and about reporting both conventions going
forward. It is the cheapest ceiling in the program: 56 → 66 with zero model change.

**5. A second scorer is not the answer.** BM25 gets only **4 of the 64** misses, so the
BM25/CE ensemble ceiling is ~60 — the two instruments fail on the same items.

**6. Ranking margin is a minor factor.** Of the 64, gold sits at rank 2 on 15 items and within 5
on 27, but beyond rank 20 on 25: when the model misses, it is usually *far* from the answer,
which is consistent with "no answerhood representation" rather than "needs a sharper score".
For the *gated* deployed architecture, 39 of the 64 (61%) have gold outside the pool and were
never candidates at all.

## Corrections recorded (not smoothed over)

- Amendment 001 wrote that X1 items have "ceiling 0 for every reranker". **Overstatement,
  corrected here:** the reranker wins 18/50 of them. The registered decision rule (candidate
  unit carries the error mass) still fires and the sub-partition numbers are unaffected.
- The `hits` descriptive "pred_same_speaker = 1.0" is **tautological** (on a hit, pred *is* gold)
  and carries no evidence; the errors-only value (0.672 same speaker, median 142 turns apart,
  72% of predictions after gold) has no matched base rate, so it is descriptive only.

## What is next (a feasibility gate, not a run)

The audit's recommendation is a **contract** change, consistent with the arc's strongest signal:
train with answer-stating turns as explicit negatives on event-anchor items (and
event-introducing turns as negatives on answer items) — a single-factor re-run of AF-PRE-005's
config, same data volume, same pool rule.

**Successor feasibility measured (`PF4_successor_negative_supply.py`, no model):** on the 1,291
AF-PRE-005 training items, **310 (24.0%)** have at least one answer-bearing non-gold turn
(median 0, p90 3). Those 310 items currently teach the model nothing about answer-vs-anchor; the
supply is real but modest — enough for a contract probe to be *feasible*, not enough to be cheap.
Two cheap additions belong in the same registration: session-header rendering in the candidate
text (+4 ceiling, X2), and reporting both gold conventions (strict earliest and any-evidence,
+10 ceiling) so the label-identity mass stops being confused for capability.

