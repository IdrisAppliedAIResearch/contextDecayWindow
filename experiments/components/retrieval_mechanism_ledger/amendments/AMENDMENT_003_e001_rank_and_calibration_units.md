# Amendment 003 - E001 Rank And Calibration Units

**Component:** Retrieval Mechanism Ledger, E001
**Timing:** Raised during implementation audit, before E001 model weights were
downloaded and before any E001 model output was generated.
**Authorization:** Owner request of July 30, 2026 to work the supplied ledger
end to end, subject to `AGENTS.md`.

## Trigger And Evidence

The prospective E001 protocol compared attention-cue cosine rank to the nine
compact N candidates that fit at 32,000 characters. AS-001's historical rank 27
is a logical N rank based on retrieval generation and turn order, not a cosine
rank. The proposed threshold therefore mixed two different orderings and could
pass without showing either K eligibility or delivery.

The calibration text also did not state whether attention argmax included the
teacher-forced answer prefix. Allowing that prefix would let a head score by
attending to earlier answer tokens instead of copying from the haystack needle.

## Change

1. Remove the rank-at-most-9 E001 criterion.
2. Keep cosine rank as a descriptive surrogate-audit field only.
3. Define the narrow F2 signal solely as reaching the carried K threshold
   `0.48`.
4. For retrieval-head calibration, use the attention row immediately preceding
   each expected code token and compute argmax only over haystack token
   positions. A hit requires the argmax position to overlap the needle's code
   span.

## Rationale

K threshold crossing is the only registered selector effect of a changed query
embedding. It still does not certify delivery because the carried packer is
N-first. Reporting rank remains useful for detecting uniform cosine shifts, but
it is not promoted to an incompatible gate.

Restricting calibration to haystack keys preserves the copy-retrieval property
the detector claims to measure.

## Exclusions

No Q4 query, target, candidate corpus, embedding model, generator revision,
quantization, head-score threshold, attention arm, or E003 disposition changes.
E001 remains exploratory and non-deployable.
