# Amendment 012: N/K Reinforcement Diagnostic And Corrected Tier 6 Rerun

**Date:** 2026-07-29
**Status:** Binding before diagnostic implementation or corrected Tier 6 code
**Registration anchor:** `b60b7084741eb5d30298261076b4bca78abe713a`
**Mechanism finding anchor:** `035ec6a1`
**Applies to:** T1.3 and T6.1 only

## Trigger And Evidence

The first 121-turn T6.1 run matched the registered delivered-character target,
but its live N order differed from the order used to calibrate the widening
settings. The calibration order was unretrieved episodes first and then the
least-recently retrieved generation. The live implementation instead placed
the most recently retrieved episodes first. Rewriting retrieval metadata after
each turn therefore reinforced the same early set.

The blinded 6.5/13.0 score was committed before this defect was known. Its
losses relative to Study 009 Arm S's corrected 9.0 occurred on Q4, Q6, and Q7,
the targeted questions for which K delivered the required source facts in Arm
S but the invalid T6.1 run delivered none. This direction is a provisional
signal that N and K are not interchangeable and that N volume does not
substitute for query relevance. It is not evidence for or against the
registered architectural conclusion because the run did not execute the
registered widening policy.

The preserved Study 009 and Study 010 Arm S retrieval logs make a direct,
offline test of the suspected reinforcement loop possible. This was an open
mechanism question when T1.3 was drafted. The repository owner directed that it
now be tested as a named T1.3 hypothesis and authorized a corrected 121-turn
rerun, with the character widening rule and an offline/live equivalence gate
locked before ablation.

## Change 1: Named T1.3 Reinforcement Hypothesis

The T1.3 supplement adds the named hypothesis
`H_T1.3_NK_REINFORCEMENT`:

> Under the carried Arm S retrieval policy, repeated N admission makes N and K
> progressively less complementary, so the fraction of K candidates already
> present in N rises over conversation position.

This is a deterministic, descriptive mechanism diagnostic. It does not alter
the completed T1.3 similarity analysis, add a retrieval candidate, advance a
method, or change any registered threshold.

### Locked Inputs

The complete preserved full-run logs are read-only:

- Study 009 Arm S:
  `experiments/study_009/runs/study_009_full_001/arm_s/logs/retrieval.jsonl`
  (121 rows; SHA-256
  `c948eaca81450cad14283b57591cdc2355011d797c885c84688d94acc37a9ddb`)
- Study 010 Arm S:
  `experiments/study_010/runs/study_010_full_001/arm_s/logs/retrieval.jsonl`
  (1,000 rows; SHA-256
  `e57dd5d170421da699abd094f304df3e783c559ca7997f183e4ad118b9e3f414`)

The implementation must verify both hashes and row counts before analysis and
again after analysis.

### Locked Per-Turn Accounting

For every logged turn `t`:

- `K_t` is the logged `k_count`.
- `O_t` is the number of `n_episodes` whose logged `retrieval_type` is `KN`.
- `U_t` is the number of logged `k_episodes`.
- The overlap fraction is `f_t = O_t / K_t` when `K_t > 0`.
- When `K_t = 0`, `f_t` is null and that turn is excluded from fraction-based
  trend calculations, while the zero-candidate turn remains in the output.

The analyzer must fail closed unless `K_t == O_t + U_t`, `n_count` equals the
number of `n_episodes`, episode IDs are unique within each delivered block,
the N and K-only blocks are disjoint, every source turn is strictly before
`t`, turn numbers are contiguous, and the expected final turn is present.

### Locked Trend Decision

Each corpus is divided by absolute conversation position into four contiguous
quartiles using:

```text
quartile(t, T) = min(4, 1 + floor(4 * (t - 1) / T))
```

For each quartile, the primary micro-overlap fraction is:

```text
F_q = sum(O_t) / sum(K_t)
```

when the quartile contains at least one K candidate. The primary change is
`delta = F_4 - F_1`.

As a direction check, ordinary least squares is fit to the evaluable per-turn
fractions `f_t` against normalized position `(t - 1) / (T - 1)`. No p-value is
used because each preserved run is a complete deterministic census, not a
sample.

A corpus supports the hypothesis only when `delta > 0` and the OLS slope is
positive. `H_T1.3_NK_REINFORCEMENT` is **CONFIRMED_ON_PRESERVED_RUNS** only
when both corpora support it. One supporting corpus is **MIXED**; neither is
**NOT_CONFIRMED**. A missing first- or fourth-quartile denominator, fewer than
two evaluable turns, or any invariant failure is **NOT_EVALUABLE**, never a
pass.

The output must include one row per turn, quartile aggregates, both trend
measures, invariant results, source hashes, implementation SHA, and a short
report. No generation or embedding call is permitted.

## Change 2: Treatment Of The Invalid 121-Turn Run

The existing run at
`tier6/runs/tier6_live_121/context_matched_stm` is permanently classified
`PROTOCOL_INVALID_FOR_ARCHITECTURAL_INFERENCE`.

- Its committed blinded 6.5 artifact and all mechanism artifacts remain
  immutable and preserved as a diagnostic record.
- Because scoring preceded discovery of the defect, the historical score file
  is retained, but 6.5 is not an eligible T6.1 arm score and may not enter a
  registered score comparison, decision table, or architectural conclusion.
- The invalid run is not rescored, relabelled as valid, overwritten, or
  deleted.
- The corrected run uses new run IDs and new output directories.

The diagnostic direction remains reportable only as a provisional mechanism
signal: extra N displaced useful K under the invalid most-recently-retrieved
implementation. The corrected rerun is required before interpreting whether
properly widened STM approaches 12.0 or remains near 9.0.

## Change 3: Frozen Corrected T6.1 Widening Rule

The corrected 121-turn rerun implements the exact character rule in
pre-registration Section 10 item 5 and Amendment 007. It does not recalibrate
or retune after the invalid result.

- N cap: exactly `32`.
- K cosine threshold: exactly `0.48`.
- Exact serialized retrieval payload cap after identity deduplication:
  `60,595` Python characters.
- Candidate and packing order: N first, then K-only.
- N order: unretrieved episodes first; then least-recently retrieved logical
  generation; source turn ascending and episode ID ascending are stable ties.
- K order: carried episode source order after thresholding, with no similarity
  rerank.
- Every admitted N or K-only episode is marked retrieved at the current logical
  turn for the next turn's N order.
- Wall-clock timestamps may remain for historical observability, but they may
  not influence corrected N selection or ordering.

The authoritative logical retrieval generation is the greatest prior
`retrieval_events.turn_number` for the episode. An episode with no prior event
is unretrieved. This state is database-backed so checkpoint resume and
uninterrupted execution use identical ordering.

No script, prompt renderer, raw episode representation, topic behavior, rule
behavior, model, seed, sampler, response budget, rubric, scorer, or
interpretation threshold changes.

## Change 4: Binding Offline/Live Equivalence Gate

Before either corrected ablation, an offline gate must compare two independent
paths over turns 1-111 of the preserved Study 009 Arm S source corpus:

1. the Amendment 007 calibration oracle using its explicit
   `last_generation` map; and
2. the corrected production retrieval engine using only database-backed prior
   retrieval events for N generation state.

The replay uses the selected `N=32`, `K=0.48`, and 60,595-character cap,
historical raw episode pairs and stored episode embeddings, and the registered
query-embedding model. At each turn it admits only source episodes with source
turn `< t`.

The gate fails unless all of the following match exactly on every turn:

- ordered eligible episode IDs;
- ordered N candidate IDs;
- ordered K candidate IDs before N/K deduplication;
- delivered N IDs and delivered K-only IDs;
- skipped and duplicate IDs;
- serialized payload bytes, SHA-256, and character count;
- post-turn logical last-generation state.

The replay must also reproduce the locked selected development vectors for
turns 92-111 from
`settings/tier6_context_match_settings.json`: delivered characters, delivered
N counts, delivered K-only counts, absolute errors, and the passing median
absolute percentage error.

A separate minimal order fixture must produce
`unretrieved -> oldest-retrieved -> newest-retrieved` in both paths. The gate
records source hashes, model hash, code SHA, all per-turn comparisons, and a
single PASS or FAIL. Any mismatch blocks ablation and inference; it requires a
new amendment rather than a relaxed comparator.

The repaired implementation, tests, unchanged settings lock, and passing
equivalence artifact must be committed in that order before the first
corrected 35-turn ablation.

## Change 5: Corrected Run Order

After the equivalence gate passes:

1. Run two independent 35-turn ablations, each on a freshly launched server.
2. Require byte-identical prompts and answers for all 35 turns and distinct
   server PIDs, as locked by Amendment 008.
3. Commit the ablation artifacts and passing gate before full inference.
4. Run one corrected 121-turn arm on a third fresh server under the unchanged
   guarded runtime.
5. Seal mechanisms, expose only the scoring surface, and complete blinded
   scoring under Amendment 009 before opening corrected mechanism logs.
6. Compare the corrected score with the committed corrected Study 009 S=9.0
   and L=12.0 benchmarks under the original T6.1 interpretation.
7. Then evaluate character match, N/K composition, targeted fact delivery,
   breadth delivery/use, and whether the invalid run's provisional signal
   replicates under the corrected policy.

The corrected run IDs are:

- `tier6_ablation_corrected_a`
- `tier6_ablation_corrected_b`
- `tier6_live_121_corrected_001`

## Rationale

The offline overlap check directly tests whether the carried retrieval
mechanism makes N increasingly absorb K, rather than inferring the loop from
one failed widened run. Freezing the trend rule before computing it prevents a
post hoc definition of "climbs."

The rerun changes no registered resource amount or retrieval factor. It repairs
the implementation so live execution matches the policy that selected the
already-committed settings. Exact replay is necessary because a character
match can pass while the information allocation is false, which is the
program's recurring surrogate-failure pattern.

## Exclusions

This amendment does not authorize the 1,000-turn extension, modify Amendment
010, add a policy level, weaken a score or gate, reopen Study 010, alter a
locked pre-registration, or permit rubric artifacts in mechanism code. It does
not turn either preserved run into a valid architectural comparison.

## Authorization

On 2026-07-29, after reviewing the invalid run's mechanism evidence, the
repository owner explicitly directed the two-corpus offline K-in-N check,
authorized folding it into T1.3 as a named hypothesis, required character
widening and the equivalence gate to be locked before ablation, required the
invalid 6.5 to remain preserved as a diagnostic, and requested confirmation on
the corrected 121-turn rerun before any decision about 1,000 turns.
