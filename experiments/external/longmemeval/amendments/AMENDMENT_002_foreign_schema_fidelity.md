# EC-001 Amendment 002 — Foreign schema fidelity

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Adaptation-record anchor:** `a65c2566e55a2063bd1904065032f86c5d0e23a9`  
**Amendment 001 anchor:** `a1dc736cece4e1aa95412c661dec94da48feaf25`  
**Status:** AUTHORIZED BEFORE SUBSET LOCK, RETRIEVAL, OR INFERENCE  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

The comprehensive structural audit required by Amendment 001 exposed three
additional properties of the pinned cleaned V1 file before subset lock or
retrieval:

1. **Duplicate raw session ids.** Thirteen questions each contain one raw
   session id twice. In all 13 cases the two session contents are
   byte-identical filler copies at different timestamps. None of the duplicate
   ids is referenced by `answer_session_ids`, and none contains `has_answer`.
2. **Timestamp order differs from file order.** In 211 questions the
   `haystack_dates` sequence is not chronological, with 3,167 adjacent
   inversions. Seventy-six questions contain at least one session timestamp at
   or after `question_date`; 44 have an annotated answer session with such a
   timestamp. Every haystack session is nevertheless presented before the
   query in the benchmark's file and prompt order.
3. **Empty source content.** Twelve source turns have empty content. None is an
   answer turn or belongs to an answer session.

The original adapter rejected duplicate ids, nonchronological timestamps, and
empty content. That rejection makes the registered full-500 run impossible.

## Change

### Duplicate session occurrences

- Preserve every session occurrence in file order, including content-identical
  duplicates.
- Give each occurrence a measurement-only key formed from its raw session id
  and zero-based file position.
- Retain the raw session id separately for benchmark evidence joins.
- Never collapse duplicate occurrences: doing so would change store size,
  recency, selection, and exact budget cost.
- Fail closed if a duplicated raw id is referenced as evidence, because the
  benchmark label would then be ambiguous between occurrences.

### File order and timestamps

- Treat file order as interaction order. It is the order in which the
  benchmark presents all history before the query.
- Preserve timestamps in the measurement-only sidecar.
- Do not sort, filter, or index using timestamps. This carries the registered
  decision that the mechanism has turn order but no temporal component.
- Record nonchronological arrays, adjacent inversions, sessions timestamped at
  or after `question_date`, and affected answer sessions in the instrument
  audit and run provenance.
- Interpret Q6 subject to this observed instrument limitation.

### Empty source turns

- Accept and preserve empty source content.
- Determine whether an episode contains one or two source turns from the
  provenance mapping, never from truthiness of rendered text.
- An empty source turn remains a source turn and pays the serialized cost of
  its adapted episode.

## Rationale

These rules preserve the foreign benchmark as delivered and prevent metadata
cleanup from becoming an unregistered mechanism. They add no retrieval signal,
do not tune selection, and do not make any criterion easier. Every source
session occurrence and turn remains represented exactly once.

## Alternatives rejected

- **Collapse duplicate sessions:** changes store size, recency, clustering, and
  budget consumption.
- **Sort by timestamp:** exposes measurement metadata to the mechanism and
  changes the benchmark's prompt order.
- **Drop sessions timestamped after `question_date`:** removes source material
  and, in 44 questions, annotated answer sessions.
- **Drop empty turns:** violates lossless foreign-store adaptation.
- **Exclude affected questions:** changes the registered benchmark population
  after inspecting its instrument.

## Exclusions

- No change to `episodic` or its carried configuration.
- No timestamp-aware retrieval, query expansion, or supersession logic.
- No post-result subset filtering.
- No reinterpretation of abstention labels: Tier 1 evidence metrics remain
  null for all 30 abstention instances, as already registered.
