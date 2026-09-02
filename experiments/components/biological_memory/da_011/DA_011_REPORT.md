# DA-011 Residual Reachable-Miss Mechanism Report

**Status:** `PRIOR_CONSUMPTION_DOMINATES`
**Protocol commit:** `a2f2f2d3`
**Mechanical preflight commit:** `d56420a9`
**Standing:** post-outcome causal audit on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 30, 2026

## Result

All 16 one-hop-reachable misses are classified without a residual class:

| Blocker | Items |
|---|---:|
| `PRIOR_CONSUMPTION` | **13** |
| `MULTI_PAIR_CONJUNCTION` | 3 |
| Wrong lexical member | 0 |
| Both members of one pair | 0 |
| Base capacity | 0 |

The protected direct context begins these questions with median 623 characters
of slack. Evidence carriers arrive with median 45 characters left, while the
minimum required evidence payload costs median 192. Carrier edge position is
p10/p50/p90 2/7/13.2.

Capacity exists initially. Earlier noncarrier links consume it before the
required carrier is reached.

## Diagnostic Counterfactuals

Changing only the overflow member to an outcome-oracle evidence member does
nothing: 970 complete, 0 gains, 0 losses. This closes wrong-member fallback as
the residual explanation.

Moving outcome-oracle carrier edges before noncarriers reaches the full one-hop
oracle:

| Diagnostic | Complete | Gains vs DA-010 | Losses | Exact p |
|---|---:|---:|---:|---:|
| `ORACLE_MEMBER` | 970 | 0 | 0 | 1.0 |
| `CARRIER_FIRST` | **986** | **16** | **0** | **3.05e-5** |

Carrier-first gains occur in five conversations: 2, 2, 7, 0, 4, and 1 across
`conv-26/30/43/44/49/50`. It is a non-deployable causal upper bound because it
uses evidence identities.

## Mechanism

DA-008 through DA-010 correctly protected direct evidence and progressively
reduced representation cost. That path recovers 35/51 one-hop-rescuable misses.
The remaining ceiling is no longer direct capacity or turn localization.

DA-004's benefit model predicts whether a one-edge whole-pack perturbation helps.
That objective has strong grouped AUC, but it is not identical to identifying
the pair that carries a question's missing evidence. Under finite slack,
lower-priority noncarriers are still admitted before residual carriers at median
rank seven. Their payloads exhaust the available linked budget.

The next lead is therefore a separately registered, grouped evidence-carrier
ranking objective. It must use evidence-blind inference features, exclude the
target conversation from training, and compare against frozen DA-004 order.
Threshold tuning or oracle carrier features on NF-004 are not authorized.

## Integrity and Boundary

All 1,098 baseline dialogue selections replay exactly. Direct 935, fallback 970,
all-eligible oracle 986, 25,941 edges, DA-004 labels and grouped AUC reproduce.
The result SHA-256 is
`6f0925b181bcb62410d4ce346601db0d73070ee7f9b69455a5285f3b73994d56`.

This is a spent-corpus causal audit. Oracle-member and carrier-first diagnostics
are not deployable rules, reader evidence, transfer, or adoption authority.

