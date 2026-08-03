# EC-001 Amendment 001 — Lossless adaptation of irregular session turns

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Adaptation-record anchor:** `a65c2566e55a2063bd1904065032f86c5d0e23a9`  
**Status:** AUTHORIZED BEFORE RETRIEVAL OR INFERENCE  
**Authorization:** Program author, August 3, 2026: “Yes, go ahead.”

## Trigger and evidence

The committed adapter required every LongMemEval session to consist entirely
of adjacent `user, assistant` pairs. The pre-result schema gate against the
pinned cleaned V1 file
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
failed before subset lock or retrieval.

Across 23,867 session instances:

- 1,951 session instances in 485 of 500 questions are not strict adjacent
  user/assistant pairs.
- 1,931 begin with one assistant turn and then contain a strict paired tail.
- 20 have another irregular role sequence.
- Eight irregular sessions are annotated evidence sessions.
- Seven irregular sessions contain a turn marked `has_answer`.

Dropping unmatched turns can therefore delete required evidence. Excluding
affected questions would remove 485 of 500 questions and violate the
registered full-benchmark scope.

## Change

Replace the strict-pair rejection with a deterministic, lossless adapter:

1. Scan every session in source order.
2. An adjacent `user, assistant` pair becomes one ordinary episode.
3. Any unmatched source turn becomes one singleton episode. An unmatched user
   occupies `user_message` with an empty `assistant_message`; an unmatched
   assistant occupies `assistant_message` with an empty `user_message`.
4. Preserve each source turn's role and content byte-for-byte in exactly one
   episode. Do not drop, merge, summarize, reorder, or rewrite source turns.
5. Preserve session id, source-turn position, episode number, timestamps, and
   `has_answer` labels in the measurement-only sidecar.
6. Add a binding gate that reconstructs the ordered source role/content
   sequence from the adapted episodes and requires exact equality.
7. Report ordinary-pair and singleton counts in pre-run and run provenance.

The `episodic` library remains unchanged. Its unit remains an episode; the
foreign-store adapter only supplies an empty counterpart where the benchmark
provides no complete exchange.

## Rationale

This is the smallest adaptation that permits the registered evaluation while
preserving all foreign evidence. It does not add a retrieval signal, tune a
parameter, or make a success criterion easier. Singleton episodes pay their
full serialized cost and participate in retrieval under the same carried
configuration as ordinary episodes.

## Alternatives rejected

- **Drop leading or otherwise unmatched turns:** deletes source content and can
  delete annotated evidence.
- **Exclude affected questions:** leaves only 15 questions and violates the
  full-500 Tier 1 scope.
- **Serialize a whole session as one episode:** changes indexing granularity,
  which EC-001 reserves for a follow-on.
- **Merge an unmatched turn into a neighboring exchange:** changes episode
  boundaries and the text embedded for that neighboring exchange.
- **Repair role labels heuristically:** rewrites the foreign instrument.

## Exclusions

- No changes to `episodic`, its renderer, selector, budget, recency window,
  embedder, or abstention behavior.
- No new session-level index.
- No use of answers, evidence labels, question types, or timestamps by the
  mechanism.
- No Tier 1 retrieval, Tier 2 generation, or scoring is authorized by this
  amendment alone. The Tier 2 subset must still be committed first.
