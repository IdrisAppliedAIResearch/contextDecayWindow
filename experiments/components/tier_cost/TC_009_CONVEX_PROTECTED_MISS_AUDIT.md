# TC-009 convex plus protected-breadth miss audit

**Type:** post-result descriptive audit; not TC-010  
**Status:** analysis lock before implementation  
**Date:** 2026-08-23  
**Parent:** TC-009 convex relevance with protected-breadth probe

## 1. Question and boundary

Explain the already-published CC80+A3 availability result at 16,000 and 32,000
characters: count every incomplete question, characterize what the treatment
gained over full-budget dense retrieval, and identify recurring properties of
the remaining misses.

The outcome is already known. This audit is post hoc and descriptive. It sets
no bar, tunes no parameter, makes no causal claim, selects no architecture,
does not run a reader, and cannot authorize TC-010.

## 2. Frozen inputs and population

Read only the committed parent selection, result and per-question artifacts.
Use all 868 eligible unique questions, the same evidence identities and the
same targeted/breadth/other population labels. Join question text, LoCoMo
category, evidence carrier and session metadata from the hash-locked corpus by
stable sample id, source index and content identity. Make zero embedding or LLM
calls and do not rerank or repack anything.

## 3. Frozen analyses

At each budget report:

1. total CC80+A3 incomplete questions and their targeted/breadth/other counts;
2. zero-evidence versus partial-evidence misses, evidence-carrier count and
   distinct evidence-session count;
3. 16k misses rescued at 32k, misses persistent at both budgets, and any 32k
   regressions;
4. treatment gains and losses versus dense, with gain labels determined only
   from the two frozen controls: `CC80_ONLY` when only full CC80 succeeds,
   `A3_ONLY` when only dense+A3 succeeds, `BOTH_CONTROLS` when both succeed,
   and `COMBINATION_ONLY` when neither succeeds; use the symmetric definitions
   for losses and call these diagnostic associations, not causal attribution;
5. for required evidence, one-based dense, CC80 and A3 ranks and whether the
   treatment admitted it through initial relevance, protected spread, returned
   relevance, or not at all;
6. counts by LoCoMo category, conversation and these structural groups:
   single carrier/single session, multiple carriers/one session, and multiple
   sessions;
7. transparent, overlapping question-text flags: `QUANTITY` for “how many”,
   “how much”, “number”, or “amount”; `TEMPORAL` for “when”, “before”, “after”,
   “first”, “last”, “earlier”, “later”, “how long”, “year”, or “date”;
   `LOCATION` for “where”, “place”, or “location”; `CAUSAL` for “why”,
   “cause”, “reason”, or “helped”; and `ENUMERATION` for “what are/were”,
   “which”, “what places/activities/causes/skills/events/jobs/things”, or
   “how many”. Questions matching none are `UNMARKED`.

Report the largest groups with denominators and compare miss rates to the full
eligible population. Do not infer difficulty from raw miss counts alone. List
the questions in every gain/loss and persistent-miss set in a machine-readable
artifact; the prose report may use representative examples without inventing
new labels.

## 4. Minimal Preflight

- **PF1:** hash and count the corpus plus parent selection/result/question
  artifacts.
- **PF2:** verify arm names against selected-id behavior and reproduce all
  published complete totals, gains and losses from the question rows.
- **PF3:** commit this lock before implementation; audit code is read-only and
  refuses a drifted input hash.
- **PF4:** no result bar exists; planted rows must reach all four association
  labels, zero/partial miss states and all admission phases.
- **PF5:** enforce unique stable `(sample_id, source_index)` joins and content
  evidence identities; reject a planted missing or duplicate join.
- **PF6:** reproduce the parent result schema, population and summaries exactly
  before emitting any audit result.
- **PF7:** not applicable; there is no feedback or mutable selection state.
- **PF8:** four development conversations can describe these misses but cannot
  establish corpus transfer.
- **PF9:** text flags, categories, ranks and control-arm associations can all
  correlate with a miss without causing it; overlapping flags and unmarked
  residuals must remain visible.
- **PF10:** this is evidence availability only, not answer accuracy or use.

## 5. Execution order

Commit this lock alone; implement and test the read-only audit; commit passing
Preflight; run once; report and close the stacked diagnostic PR. Do not alter
the parent probe, its locked selections, or any TC component.
