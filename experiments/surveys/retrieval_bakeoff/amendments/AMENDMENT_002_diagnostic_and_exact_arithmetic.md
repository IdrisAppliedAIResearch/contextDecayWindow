# Amendment 002 - Diagnostic Attribution And Exact Recall Arithmetic

**Survey:** Retrieval Bakeoff
**Registration anchor:** `b60b7084741eb5d30298261076b4bca78abe713a`
**Executable protocol anchor:** `d6d80fbb`
**Original T1-T3 result anchor:** `29c5150d`
**Status:** BINDING BEFORE CORRECTED ANALYSIS
**Scope:** T1.3 attribution and T2/T3 arithmetic only

## 1. Trigger And Evidence

The first registered T1-T3 run completed without source mutation and committed
all raw retrieval and evaluation rows. Audit of those immutable rows exposed
two measurement defects.

First, the T1.3 helper labelled the mechanism
`stored_embedding_drift_or_corruption` whenever fewer than 100% of recomputed
vectors were byte-identical to persisted vectors. That condition was not a
registered criterion and is not causally sufficient. Study 009 reproduced
historical K=0 and Study 002 reproduced historical K=5 under both stored and
recomputed similarity distributions. Small vector differences therefore did
not cause either threshold outcome. The two stores also contain different
historical turn-120 query strings and 67/119 non-identical user strings because
the earlier run predates the documented script-encoding correction.

Second, pooled M1 and M6 enumeration recall are both exactly `23/96`. Binary
floating aggregation represented them as `0.23958333333333331` and
`0.23958333333333334`, causing the strict-increase check to call an exact tie a
win. This is the standing surrogate failure in numerical form: representation
noise passed a semantic comparison.

## 2. Preserved Evidence

Nothing under `tier1/`, `tier2/`, or `tier3/` at `29c5150d` is edited. The
original output, including both defects, remains the audit trail. Corrected
artifacts are additive under:

`experiments/surveys/retrieval_bakeoff/corrections/amendment_002/`

No retrieval method is rerun for the arithmetic correction. It consumes the
committed `tier2/evaluation_results.jsonl` rows byte-for-byte.

## 3. Corrected T1.3 Protocol

Each historical store uses its own persisted turn-120 user message as its query.
The diagnostic reports:

1. similarity against persisted episode embeddings;
2. similarity after re-embedding the exact historical
   `User: ...\nAssistant: ...` pair text;
3. similarity after embedding the historical user message alone;
4. turn-aligned counterfactual pair embeddings formed by holding one run's user
   message and query fixed while swapping in the other run's assistant response;
5. exact user-message equality, differing-turn count, assistant-response
   character distributions, and threshold crossings.

Persisted vectors are the authority for historical-path reproduction. A vector
replay difference may be called causal drift only when it changes a candidate's
side of the 0.50 threshold and makes the recomputed K count disagree with the
committed historical K count. Byte inequality alone is descriptive.

Attribution follows these fixed rules:

- `assistant_response_content_shift` when each stored distribution reproduces
  its historical K count and assistant swapping materially changes a K count
  while user/query are held fixed;
- `script_encoding_or_user_text_shift` when assistant swapping does not change
  the outcome but using the alternate historical user/query text does;
- `stored_embedding_drift` only under the threshold-crossing condition above;
- `not_isolated` otherwise.

The full corrected distribution and every counterfactual score are retained.

## 4. Exact Recall Arithmetic

All recall aggregation and strict comparisons use
`fractions.Fraction(matched_fact_count, required_fact_count)`.

- Query macro means are exact sums divided by exact query counts.
- Equal-corpus pooling is an exact sum divided by two.
- A win requires exact `candidate > baseline`.
- The 10% non-regression check is exact
  `candidate >= Fraction(9, 10) * baseline`.
- Floats remain display fields only. Every corrected aggregate also records its
  exact numerator and denominator.

T3 winner selection and oracle recall use the same exact values. Precision and
latency remain floating tie-breakers only after exact recall equality.

## 5. Consequences And Exclusions

- No answer key enters mechanism code.
- No query, candidate, score, serialized block, latency, or index cost changes.
- No advancement threshold is weakened.
- M6's enumeration result is corrected from a win to a tie; its advancement
  status is recomputed from all three classes rather than stipulated here.
- T1.2's 8/17 ceiling is unchanged.
- Tier 4 and Tier 5 consume only the corrected advancement and winner tables.

## 6. Authorization

The repository owner authorized end-to-end execution and amendments in the
2026-07-28 instruction: "Follow it end to end. Amendments are allowed if
needed."
