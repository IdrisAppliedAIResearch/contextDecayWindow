# Amendment 007: Tier 6 Calibration Target

**Date:** 2026-07-28  
**Status:** Binding before Tier 6 implementation, calibration, or inference  
**Applies to:** T6.1 only

## Trigger And Evidence

The locked widening rule requires pure STM to match Study 009 Arm L on exact
serialized delivered retrieval characters after deduplication. It defines the
unit but not the turns used for calibration, whether all delivered retrieval
blocks are charged, how indivisible raw episodes are packed, or how N and K are
selected when more than one setting is close.

Those omissions permit incompatible implementations. Matching the nominal
32,000-character LTM allocation would omit Arm L's carried N/K payload. Matching
rubric turns would tune on live evidence. Matching episode counts could pass
while delivered characters differ by tens of thousands, repeating the
surrogate-budget failure documented in `AGENTS.md`.

The immutable Study 007 Condition C artifact reused as Study 009 Arm L provides
complete prompts for every turn. On development turns 92-111, the exact
deduplicated retrieval payload has a median length of **60,595 characters**.
The per-turn range is 59,387-62,223 characters. These values include the
serialized N, K-only, and LTM blocks but exclude pinned rules, the system
prompt, the current query, and the response suffix.

## Change

### Calibration Data

Calibration uses only turns 92-111. Arm L supplies the target character vector.
The preserved Study 009 Arm S database supplies candidate raw episodes,
embeddings, topic labels, and response text. At turn `t`, only Arm S episodes
with source turn `< t` are eligible. Turns 112-121, all answer keys, all rubric
criteria, and every live T6.1 answer are prohibited from calibration.

The target vector is extracted from:

`experiments/study_007/runs/study_007_full_001/condition_c/constructed_prompts`

The candidate raw store is:

`experiments/study_009/runs/study_009_full_001/arm_s/study.db`

Both source artifact hashes are recorded in the settings artifact.

### Charged Payload

For Arm L, the charged payload is exactly:

```python
"\n\n".join([recent_context, retrieved_stm, retrieved_ltm])
```

For widened STM, it is exactly:

```python
"\n\n".join([recent_context, retrieved_stm])
```

Each block is produced by the carried production XML renderer after
episode-identity deduplication. Python `len()` charges outer tags, attributes,
escaping, indentation, newlines, and the two-newline block separators. Empty
blocks remain charged. No padding, truncation, synthetic content, or unrendered
accounting may be used to improve the match.

The fixed widened-STM payload cap is **60,595 characters**, the Arm L
development median. A candidate that would exceed the cap is skipped; later
smaller candidates remain eligible.

### Candidate Settings

The carried N/K policy is widened without adding a new ranker:

- N caps: `12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40`.
- K cosine thresholds: `0.48, 0.45, 0.40, 0.35`.
- N retains decay order. Because decay is monotonic in last retrieval time,
  calibration represents it as unretrieved first, then least-recently
  retrieved generation, with source turn and episode ID as stable ties.
- K retains the carried episode source order after thresholding. It is not
  re-ranked by similarity.
- N has precedence over K for identity deduplication. Packing traverses N first,
  then K-only, matching the carried block order.
- Every admitted episode is marked retrieved for the next calibration turn,
  matching the carried metadata update.

All 60 N/K cells are evaluated. For each cell, the primary loss is mean
absolute character error against Arm L's 20-turn target vector. Ties resolve by
lower maximum absolute error, then lower N cap, then higher K threshold. This
selects the smallest departure from the carried policy after character match.

The selected cell must have median absolute percentage error at most 5%.
Failure blocks the live run and requires a new authorized amendment; it may not
be repaired by widening the grid after inspecting live answers.

### Artifact And Commit Order

Calibration writes a standalone settings artifact containing the source
hashes, target vector, all 60 candidate rows, selected settings, exact loss
values, match-gate result, and leakage scan. The artifact and implementation
tests are committed before the 35-turn ablation or any full live inference.

## Rationale

The mature development window is the closest answer-independent proxy for the
steady-state context delivered at the terminal probes. Charging all retrieval
blocks measures the resource the model actually receives rather than one
tier's nominal allocation. The fixed grid and smallest-departure tie-breakers
prevent post hoc tuning while allowing indivisible raw episodes to approach the
target without meaningless whitespace.

## Exclusions

This amendment does not change the 121-turn horizon, script, seed, generation
settings, response budget, raw episode text, production XML representation,
locked rubric, scoring protocol, score-before-logs order, or the conditional
1,000-turn rule in Amendment 004. It does not authorize answer-key access by
retrieval, ranking, packing, runtime, or calibration code.

## Authorization

The repository owner authorized necessary bakeoff amendments and specifically
authorized the 121-turn T6.1 interpretation on 2026-07-28. This amendment
resolves only the execution ambiguity required to carry out that authorized
test.
