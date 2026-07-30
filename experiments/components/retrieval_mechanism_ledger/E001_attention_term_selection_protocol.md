# E001 Attention-Derived Term Selection Protocol

**Status:** PROSPECTIVE - no E001 model output generated
**Type:** Exploratory offline diagnostic, not a study or pre-registration
**Parent:** `RETRIEVAL_MECHANISM_LEDGER.md`, E001
**Deployment status:** Not deployable

## Validity Correction

The supplied ledger labels E001 an oracle for "perfect term selection." Model
attention is a heuristic signal, not perfect selection. The registered Q4-only
probe can test the F2 identity cue, but it cannot bound F1 breadth and therefore
cannot authorize or kill E003 as a family-wide mechanism.

The current K path is thresholded but not similarity-sorted, and exact N-first
packing can still exclude a K candidate. E001 will report cosine, corpus rank,
K-threshold crossing, and a hypothetical similarity-ranked 32k reachability
marker. None is reported as live delivery.

The ledger's `0.16612689197063446` Q4 baseline is superseded. The corrected
baseline is `0.12042197585105896`, as already recorded in `ERRATA.md` and
AS-001.

## Locked Inputs

- Probe: corrected Tier 6 turn 115 Q4 query.
- Target: the turn-55 raw episode.
- Corpus: every raw episode with `source_turn < 115` in the corrected Tier 6
  database.
- Candidate representation: the carried stored episode embeddings.
- Cue embedder: Qwen3-Embedding-0.6B Q8_0, SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`.
- Generator: `Qwen/Qwen3.6-27B`, Hugging Face revision
  `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`.
- Generator quantization: bitsandbytes NF4 4-bit, double quantization,
  BF16 compute.
- Attention implementation: eager.
- Full-attention layers: every layer whose locked model config declares
  `full_attention`; linear-attention layers are excluded because they do not
  expose the same token-by-token matrix.
- Track 1 reference commit: `15338a4`; no Track 1 file is imported at runtime.

All model, input, source, package, GPU, and implementation hashes are recorded.
The corrected source seal and leakage gate must pass before the generator loads.

## Independent Retrieval-Head Calibration

Retrieval-head IDs are model-specific and will not be borrowed from another
architecture. Calibration uses 32 deterministic copy cases: eight fixed vault
labels crossed with four needle positions in a fixed 24-sentence synthetic
haystack. Each needle states a label-specific six-digit access code; the query
asks for that code.

The exact expected answer is teacher-forced after the query. For each
full-attention head and each expected answer token, record whether its
highest-attended prompt token is an occurrence of the same token inside the
needle's code span. A head's retrieval score is the mean of that indicator over
all answer tokens and cases. Following Wu et al., heads with score at least
`0.1` form the retrieval-head arm. Calibration data are generated from constants
in mechanism code and are independent of Q4, study facts, and rubric files.

Fail closed if no head crosses `0.1`, any case/token mapping is ambiguous, or a
deterministic calibration rerun changes selected head IDs or scores.

## Q4 Probe And Sweep

Tokenize the exact query without a system prompt or chat wrapper and append one
EOS token so the final query token can receive attention from a later position.
Run one forward pass and capture every full-attention matrix.

Probe every causal row from the second query token through the appended EOS.
For each row, form two attention distributions over visible query tokens:

1. average over every full-attention layer and head;
2. average over the independently calibrated retrieval heads.

Map subword tokens to maximal non-whitespace query units using tokenizer offset
mappings. Sum subword attention within each unit. For every probe row and arm,
sweep `k` over every integer from `1` through the number of visible units.
Select the top `k` units by descending attention, breaking ties by original
unit position; embed selected units in original query order, joined by one
space.

For every cue report:

- selected units and attention mass;
- target cosine and corrected-baseline delta;
- target rank among all eligible episodes, with deterministic episode-ID ties;
- whether cosine reaches the carried K threshold `0.48`;
- whether rank is at most 9, the exact number of compact N candidates that fit
  the 32k AS-001 point.

The unmodified full query is a baseline row. The raw attention tensors and every
sweep row are written before descriptive selection of a best row.

## Interpretation

**Narrow F2 signal:** present only if a cue either reaches cosine `0.48` or
improves the target to rank 9 or better. Otherwise attention-derived selection
is killed for this Q4 diagnostic.

This threshold measures whether the target could enter a relevant candidate set;
it does not claim delivery under the unchanged N-first packer.

**Family decision:** E001 cannot bound breadth because it has no Q11 arm. E003
therefore remains `NOT_AUTHORIZED` regardless of E001's narrow F2 result. A
future E003 authorization requires its own prospective breadth bound, storage
multiplier, exact-budget policy, and no-regression test.

## Required Artifacts

- environment and source manifest;
- generator model manifest and config;
- fixed calibration cases and per-head scores;
- calibrated retrieval-head IDs;
- raw Q4 attention tensors or lossless per-row matrices;
- complete cue sweep;
- baseline reproduction;
- deterministic rerun hashes;
- leakage audit with a planted forbidden-path failure;
- report that states Q4 quantization and the narrow non-deployable scope.
