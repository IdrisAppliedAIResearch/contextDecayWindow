# AF-PRE-008 — CLOSED AT PART-1 FEASIBILITY (not registered, not run) 2026-09-20

**Proposal (user, after AF-PRE-006):** AH-salience — the question-independent anchor
detector — ranks every turn by "how anchor-like is this turn given its context", the
top candidates form the pool, and the trained reranker picks with the question. This
would replace the BM25/regex pool as an *architecture* change. The number that motivated
it was AF-PRE-006's AH-salience 71/120 (59%) vs 1/9 chance.

PREFLIGHT Part 1 requires characterizing the mechanism on real data before designing a
test of it. That characterization kills the design, so no probe was registered: registering
a run whose bar is arithmetically unreachable is a PF4 violation, not discipline.

## Part-1 measurement (`PART1_explore.py` → `PART1_results.json`)

Set: **sample-120 dev only** (`part1e_locomo_pool.json`) — unseen by both ckpt2 and ckptM.
sample2 was never touched. AH scorer = AF-PRE-006 `ckptM`, its frozen contract
(`Conversation so far:` + the 10 preceding turns, no question). Median conversation = 663 turns.

| measure | AH-salience | BM25 |
|---|---|---|
| nine-way discrimination (gold vs 8 random) | 62/120 (52%) — reproduces 006 | — |
| gold-in-pool, m=5/10/15/20/30 | 4 / 5 / 7 / 8 / 11 | 55 / 60 / 66 / 72 / 73 |
| pool → ckpt2 rerank accuracy, same m | 4 / 2 / 3 / **4** / 7 | 48 / 50 / 54 / **56** / 55 |

Global rank of the gold anchor by AH score: median **128** (p25 57, p75 273, p90 426);
gold in AH top-20 on **6.7%** of items, top-30 on 9.2%. Median relative position 0.208
(chance 0.5) — a real but far too weak global signal to pool on.

## Why the 59% did not transfer

It was never a ranking number. Distinguishing an anchor from **8 randomly drawn turns**
needs only "anchor-like vs irrelevant"; pooling needs "rank above the other ~660 real
turns", most of which are topically adjacent. The mild global shift (0.208 vs 0.5) is
consistent with both. `PART1_results.json` also records Spearman(AH score, turn length)
= **0.404**: part of what the AH head calls "anchor-like" is verbosity — §3's surrogate
failure, caught by measurement rather than by a lost run.

## The bar was unreachable, not merely missed

- PASS would need ≥ 61/120 net +5 over 56; the AH pool contains gold on 8/120 items at
  m=20, so its ceiling is **8/120**.
- The E bar (17/17) is unreachable too: AH gold rank in the 17 E-gap histories is median
  108, gold in pool **0/17 at every m** — the AH contract was trained on LoCoMo turns and
  does not transfer to E episode text.
- Soft use is nearly as closed (`PART1_union_gate.py`): the registered pool rule recalls
  73/120; adding AH-top-m by union gives 75 / 76 / 77 / 82 at m=10/20/30/50 — **at most +4**
  gold at a pool size the reranker already handles worse (its own top-20→top-30 fall-off
  is 56→55). No reachable bar for a fusion probe either.

## What is closed (and what is not)

Closed: **AH-salience as a pool rule, and as a pool-set union partner, at this
mechanism's strength, on LoCoMo conversation-scale candidate sets.** Not closed: AH-salience
as a *feature* in a scored reranker (it carries a genuine 0.208-vs-0.5 global shift), which
would need a training-time change rather than an inference-time pool, and would have to beat
AF-PRE-005's 56 the same way. Not closed: whether a stronger AH model (more data, longer
context, contrastive rather than listwise) pools better — that is a different mechanism.

This is the useful kind of negative: the idea cost ten minutes of measurement instead of a
registered run, and it explains AF-PRE-006's odd result (high nine-way salience, zero
transfer to ranking) with one mechanism — **candidate-set scale**, not task mismatch.
AF-PRE-005's 56/120 stands as the program's reranker; no architecture change is justified.
