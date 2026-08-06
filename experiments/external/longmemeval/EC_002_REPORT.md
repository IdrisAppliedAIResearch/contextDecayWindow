# EC-002 - K-First Packing Counterfactual

**Pre-registration:** `EC_002_k_first_packing.md` at
`8c75d7e22258c56cb6b422c0dfcc013cddd65613`  
**Amendment 001:** `2a675eefcf2fc53fb0d54894f7134e05dabcbdf4`  
**Amendment 002:** `1e2410c4288e1ee722daa21f41dd55010f218591`  
**Status:** COMPLETE  
**Outcome:** PACKING PRIORITY IS A CAUSAL DELIVERY GATE

## 1. Result

EC-002 changed one thing in an offline replay of the 500 EC-001 stores:
packing order. A0 packed recency, then thresholded similarity (K), then A3
coverage. A1 packed K, then recency, then A3 coverage. The dataset, store,
vectors, threshold, selector, 32,000-character budget, and measurement were
held fixed. No reader inference or embedding call occurred.

The primary any-evidence-session outcome rose from **109/470 (23.2%)** to
**261/470 (55.5%)**, a gain of **152 questions (32.3 percentage points)**.
The paired result is 152 gains, 0 losses, and 318 unchanged. Under the
registered rule, packing priority is therefore a causal gate for recovered
EC-001 items.

Exact-answer-turn-any availability rose from **79/470 (16.8%)** to
**196/470 (41.7%)**, a net gain of 117 questions (24.9 percentage points):
119 gains, 2 losses, and 349 unchanged. The two losses are disclosed as
`4f54b7c9` and `852ce960`.

No materiality threshold was registered. These are exact paired counts, not a
claim of statistical significance or reader-level accuracy.

## 2. Registered outcomes

| Outcome | A0 | A1 | Gains | Losses | Net |
|---|---:|---:|---:|---:|---:|
| Any evidence session | 109/470 | 261/470 | 152 | 0 | +152 |
| All evidence sessions | 34/470 | 137/470 | 103 | 0 | +103 |
| Any exact answer turn | 79/470 | 196/470 | 119 | 2 | +117 |
| All exact answer turns | 20/470 | 106/470 | 86 | 0 | +86 |

Within the 401-question subset whose evidence session ranked in the top four,
any-session recall rose from 96 to 248: 152 gains and no losses. K-first
packing therefore resolves much of the rank-to-delivery contradiction without
changing rank.

## 3. Strata

| Stratum | n | Any session A0 -> A1 | Gains/losses | Any turn A0 -> A1 | Gains/losses |
|---|---:|---:|---:|---:|---:|
| Knowledge update | 72 | 20 -> 50 | 30/0 | 16 -> 36 | 21/1 |
| Multi-session | 121 | 34 -> 70 | 36/0 | 29 -> 54 | 26/1 |
| Single-session assistant | 56 | 19 -> 52 | 33/0 | 7 -> 45 | 38/0 |
| Single-session preference | 30 | 1 -> 6 | 5/0 | 1 -> 5 | 4/0 |
| Single-session user | 64 | 10 -> 28 | 18/0 | 6 -> 21 | 15/0 |
| Temporal reasoning | 127 | 25 -> 55 | 30/0 | 20 -> 35 | 15/0 |

Every answerable stratum gains any-session recall and none loses an
any-session item. Single-session preference remains the weakest at 6/30; the
packing change does not remove the separately observed `K = 0.48` threshold
gate.

## 4. Mechanism

All 500 blocks remain truncated and the median delivered size remains 31,920
characters. The median path counts also remain 16 recency, 0 K, and 1
coverage, which shows why medians concealed the change. Aggregate delivered K
episodes rise from **26 to 476**, while recency episodes fall from 8,247 to
7,973 and coverage rises from 429 to 461. Total delivered episodes rise from
8,702 to 8,910.

This is a priority effect under a binding budget, not a capacity increase.
K-first gives already-thresholded similarity candidates first claim on the
same 32,000 characters. It does not test a different threshold, recency
window, episode granularity, selector, embedder, or budget.

## 5. Reproduction and cache integrity

The original EC-001 embedding cache was not retained. Amendment 001 therefore
correctly labels A0 a **reproduction under recomputed embeddings**, not a
byte-exact replay. Its mechanical gate passed all 500 questions: recency and K
identities, outcomes, and the registered rank tolerance passed; one permitted
coverage-only selection difference was fully disclosed.

EC-001 remains permanently unreplayable at bit granularity. It is
reproducible in aggregate under the amended gate. CC-006 does not repair the
past record; it protects retained caches for later runs.

A1 used the adopted CC-006 cache read-only:

- 96,585 exact solo-call float32 vectors;
- file SHA-256
  `e8a31513700a0a5d1cfe34b4703bbe3c8c85dc3ca29188d7cc480c2e2417a7ad`;
- canonical content SHA-256
  `d60d723dea787b0d5bbd25a3c89f2a1c20b92a2a79813f34688a12e7c346a180`;
- 251,232 hits, zero misses, zero new model calls;
- unchanged file hash after A1 and no SQLite journal sidecar.

The same-store A0 gate passed 500/500 before A1 output was accepted. The full
repository suite passed 1,093 tests.

## 6. Interpretation boundary

EC-002 confirms the cheap diagnostic: recency-first packing was a major causal
gate in EC-001. It does not authorize a production change. The pre-registration
requires any live Tier 2 promotion to be separately registered, because moving
availability is not proof that the reader will use the recovered evidence
correctly and the two exact-turn losses must remain visible.

The result also leaves residual failure: K-first still recalls no evidence
session on 209/470 answerable questions and exact answer-turn-any availability
remains 196/470. Thresholding, exchange/session granularity, and ranking remain
possible downstream constraints.

## 7. Artifacts and closeout

The authoritative paired artifact is
`runs/ec002_k_first/a1_k_first/paired_comparison.json`, SHA-256
`6f18b46f7316f8dcf057f7a1fa421c83a3705834d2b80a3e01bde1517a917e24`.
The source-integrity record has SHA-256
`c21d1404319204abfc4fba0313965d15569391966af5985f6dbd4944e5a08c60`.
A1 artifacts were committed at
`4168a05c890dfb50ed113748965c1d6aa6c7afb7` before this interpretation.

- [x] Report carries the pre-registration SHA.
- [x] A0 binding gate committed before A1.
- [x] A1 evidence committed before interpretation.
- [x] README and AGENTS digest updated.
- [x] Memory, ledger, errata, claim map, evidence index, and paper updated.
- [x] All run artifacts committed; cache and local logs preserved.
- [x] Separate study pull request opened: PR #40.
