# TC-007 Research Memory Update

TC-007 is complete at `REGISTERED-OFFLINE`. It tested the requested fixed-budget
dual-route architecture: dense ranked relevance receives a protected half,
A3 or facility-location spread receives the other half, duplicates merge once,
and unused spread allowance returns to relevance. The control gives dense
relevance the full 16k or 32k context.

No split is selected. A3 complete evidence versus dense is 739 vs 749 at 16k
and 812 vs 810 at 32k over 868 eligible questions. Breadth is 13 vs 16 and 27
vs 27; targeted is 637 vs 643 and 681 vs 680. No A3 direction clears the
registered signal family, so it is `MIXED_OR_NO_DIFFERENCE`.

Facility location is worse: combined complete delivery is 692 vs 749 at 16k
and 774 vs 810 at 32k. Targeted is down 40 and 23; breadth is down 7 at both
budgets. Dense clears the registered works rule at both budgets, so facility's
disposition is `CONTROL_WORKS`.

Spread was active and did add evidence dense missed, but not enough. A3 adds
5 and loses 14 evidence identities at 16k; at 32k it adds 7 and loses 3.
Facility adds/loses 9/80 and 17/63. Every treatment-only evidence identity came
through spread. A3 therefore has a small real 32k coverage effect, but it does
not improve complete breadth answers or satisfy the joint two-budget rule.

The ownership surrogate is large and misleading: A3's spread arm owns 88/86
evidence identities at 16k/32k, while only 5/7 are incremental over dense.
Protected spend, cluster touch, or spread ownership must not be reported as
additional answer evidence.

The registered selection is `NO_SPLIT_SELECTED`; `A_RELEVANCE_FULL` remains the
frozen fallback. This does not establish that every spread share fails. It tests
only 50/50 with the frozen A3 and facility orders. Budget ratios, enterprise
scaling, alternate coverage objectives, and reader accuracy remain open.

Final G0 reproduced TC-003 C5, all 2,613 TC-005 dense payloads, 3,484 treatment
traces, and 1,742 sham payloads; 2,198 tests passed. The accepted run used two
fresh processes and reproduced file digests exactly. It had 2,247 cache hits,
zero misses, zero embedding calls, and zero LLM/generative calls. Programme
model-free means no LLM calls; embedding models are counted separately.

Two pre-acceptance harness stops are preserved in history: nondeterministic gzip
header metadata and an `eligible`/`combined` aggregate label mismatch. Neither
changed the registered science. Each repair was committed and followed by a
new G0; only the final-gated run was accepted.

TC-006 was not started. Any reader validation remains a new, separately
preflighted and pre-registered study using frozen contexts and a fact-use
instrument fine enough for the observed margin.
