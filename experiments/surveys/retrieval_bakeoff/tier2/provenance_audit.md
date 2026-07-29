# Tier 2 Provenance-Violation Audit

**Source artifact:** `evaluation_results.jsonl`

**Verdict:** VALID FOR EXACT-PROVENANCE RECALL; NOT VALID FOR AN
UNQUALIFIED SEMANTIC-RETRIEVAL CLAIM

## What The Violations Were

The evaluator searched each rendered candidate for the answer-key terms, then
required both the registered source turn and registered source role before
crediting a fact. A provenance violation means the terms appeared in a
candidate from the wrong turn, the wrong role, or both.

| Measure | Count |
|---|---:|
| Evaluation rows | 528 |
| Rows with at least one violation | 62 |
| Violation events | 257 |
| Wrong turn only | 1 |
| Wrong role only | 154 |
| Wrong turn and role | 102 |
| Violating candidates credited | 0 |

Violating rows by method: M1 4, M2 9, M3 8, M4 8, M5_span 25, and M6 8.
By corpus: c121_l 22, c121_s 21, c1000_l 8, and c1000_s 11.

## What They Invalidate

The collisions show that answer-key terms can occur outside their registered
provenance. Tier 2 therefore cannot support the broad statement that a method
retrieved the intended semantic fact merely because matching words appeared.
The original status `COMPLETE_WITH_PROVENANCE_VIOLATIONS` is not a clean
architectural result.

## What They Do Not Invalidate

`src/retrieval_bakeoff/evaluation.py` records a violation and continues without
credit unless both `turn_ok` and `role_ok` are true. Inspection of all 257
events found zero cases where a violating candidate was the credited
`fact_matches` candidate. The violations therefore did not inflate
`matched_fact_count`, fact recall, domain coverage, or any advancement
numerator.

The bounded conclusion is that Tier 2's exact-source recall comparisons and
mechanical advancement arithmetic remain usable as routing inputs to later
registered tiers. They do not establish that M3, M4, M5_span, or M6 is a
generally superior semantic retriever.
